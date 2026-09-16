const CLASSES = Object.freeze({
  T1: ["Warrior", "Mage"],
  T2: ["Knight", "Duelist", "Sorcerer", "Sage"],
  T3: ["Paladin", "Berserker", "Archmage", "Arcanist"],
  T4: ["Guardian", "Conqueror", "Destroyer", "Dominator"],
  T5: ["Templar", "Ravager", "Magister", "Prophet"],
  T6: ["Justicar", "Marauder", "Arcanarch", "Hierarch"],
  T7: ["Vindicator", "Doomreaver", "Thaumaturge", "Demiurge"]
});

const SCORES = Object.freeze({ S: 4, A: 3, B: 2, C: 1 });

function responseHeaders(request, env) {
  const origin = request.headers.get("Origin");
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "Vary": "Origin"
  };
  if (origin === env.ALLOWED_ORIGIN) headers["Access-Control-Allow-Origin"] = origin;
  return headers;
}

function json(request, env, body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: responseHeaders(request, env)
  });
}

function validBrowserRequest(request, env) {
  const origin = request.headers.get("Origin");
  return !origin || origin === env.ALLOWED_ORIGIN;
}

async function hashVoter(voterId, salt) {
  const bytes = new TextEncoder().encode(`${salt}:${voterId}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, "0")).join("");
}

function gradeForAverage(average) {
  if (average >= 3.5) return "S";
  if (average >= 2.5) return "A";
  if (average >= 1.5) return "B";
  return "C";
}

async function tierResults(env, tier) {
  const [ballotResult, voteResult] = await env.DB.batch([
    env.DB.prepare("SELECT COUNT(*) AS total FROM ballots WHERE tier = ?").bind(tier),
    env.DB.prepare(`
      SELECT v.class_name,
             COUNT(*) AS vote_count,
             AVG(v.score) AS average_score,
             SUM(CASE WHEN v.grade = 'S' THEN 1 ELSE 0 END) AS s_votes,
             SUM(CASE WHEN v.grade = 'A' THEN 1 ELSE 0 END) AS a_votes,
             SUM(CASE WHEN v.grade = 'B' THEN 1 ELSE 0 END) AS b_votes,
             SUM(CASE WHEN v.grade = 'C' THEN 1 ELSE 0 END) AS c_votes
      FROM votes v
      JOIN ballots b ON b.id = v.ballot_id
      WHERE b.tier = ?
      GROUP BY v.class_name
    `).bind(tier)
  ]);

  const rows = new Map(voteResult.results.map(row => [row.class_name, row]));
  return {
    tier,
    ballotCount: Number(ballotResult.results[0]?.total || 0),
    classes: CLASSES[tier].map(name => {
      const row = rows.get(name);
      const average = Number(row?.average_score || 0);
      return {
        name,
        voteCount: Number(row?.vote_count || 0),
        average: Number(average.toFixed(2)),
        grade: row ? gradeForAverage(average) : null,
        distribution: {
          S: Number(row?.s_votes || 0),
          A: Number(row?.a_votes || 0),
          B: Number(row?.b_votes || 0),
          C: Number(row?.c_votes || 0)
        }
      };
    })
  };
}

function validateBallot(body) {
  if (!body || typeof body !== "object") return "Invalid request body.";
  if (!Object.hasOwn(CLASSES, body.tier)) return "Invalid class tier.";
  if (typeof body.voterId !== "string" || body.voterId.length < 16 || body.voterId.length > 128) return "Invalid browser identifier.";
  if (!body.votes || typeof body.votes !== "object" || Array.isArray(body.votes)) return "Votes must be an object.";

  const expected = CLASSES[body.tier];
  const submitted = Object.keys(body.votes);
  if (submitted.length !== expected.length || expected.some(name => !submitted.includes(name))) return "Every class in the selected tier must be graded exactly once.";
  if (submitted.some(name => !expected.includes(name))) return "The ballot contains a class outside the selected tier.";
  if (expected.some(name => !Object.hasOwn(SCORES, body.votes[name]))) return "Grades must be S, A, B, or C.";
  return null;
}

async function submitBallot(request, env) {
  if (!env.VOTER_SALT) return json(request, env, { error: "Voting service is not configured." }, 503);
  const length = Number(request.headers.get("Content-Length") || 0);
  if (length > 12_000) return json(request, env, { error: "Request body is too large." }, 413);

  let body;
  try {
    body = await request.json();
  } catch {
    return json(request, env, { error: "Request body must be valid JSON." }, 400);
  }

  const validationError = validateBallot(body);
  if (validationError) return json(request, env, { error: validationError }, 400);

  const voterHash = await hashVoter(body.voterId, env.VOTER_SALT);
  const statements = [
    env.DB.prepare("INSERT INTO ballots (tier, voter_hash) VALUES (?, ?)").bind(body.tier, voterHash),
    ...CLASSES[body.tier].map(name => env.DB.prepare(`
      INSERT INTO votes (ballot_id, class_name, grade, score)
      SELECT id, ?, ?, ? FROM ballots WHERE tier = ? AND voter_hash = ?
    `).bind(name, body.votes[name], SCORES[body.votes[name]], body.tier, voterHash))
  ];

  try {
    await env.DB.batch(statements);
  } catch (error) {
    if (String(error).includes("UNIQUE constraint failed")) {
      return json(request, env, { error: "This browser has already voted for this tier.", code: "ALREADY_VOTED" }, 409);
    }
    console.error("Ballot insert failed", error);
    return json(request, env, { error: "The vote could not be saved." }, 500);
  }

  return json(request, env, { accepted: true, results: await tierResults(env, body.tier) }, 201);
}

export default {
  async fetch(request, env) {
    if (!validBrowserRequest(request, env)) return json(request, env, { error: "Origin not allowed." }, 403);
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      const headers = responseHeaders(request, env);
      headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS";
      headers["Access-Control-Allow-Headers"] = "Content-Type";
      headers["Access-Control-Max-Age"] = "86400";
      return new Response(null, { status: 204, headers });
    }

    if (request.method === "GET" && url.pathname === "/api/health") {
      return json(request, env, { ok: true });
    }

    if (request.method === "GET" && url.pathname === "/api/results") {
      const tier = url.searchParams.get("tier");
      if (!tier || !Object.hasOwn(CLASSES, tier)) return json(request, env, { error: "Invalid class tier." }, 400);
      return json(request, env, await tierResults(env, tier));
    }

    if (request.method === "POST" && url.pathname === "/api/votes") return submitBallot(request, env);
    return json(request, env, { error: "Not found." }, 404);
  }
};
