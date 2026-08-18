from pathlib import Path
import re

p = Path('sxs-primo-calculator/index.html')
h = p.read_text(encoding='utf-8')

if 'Multi-Season Primostar & Realm Planner v27' in h:
    print('Already v27')
    raise SystemExit(0)
if 'Season & Realm Planner v24' not in h:
    raise SystemExit('Expected v24 calculator not found')

h = h.replace('<title>Sword x Staff — Season & Realm Planner v24</title>', '<title>Sword x Staff — Multi-Season Primostar & Realm Planner v27</title>', 1)
h = h.replace('<div class="eyebrow">Sword x Staff · season optimizer</div>', '<div class="eyebrow">Sword x Staff · multi-season optimizer</div>', 1)
h = h.replace('<h1>Season Score, EXP & Material Realm Planner</h1>', '<h1>Primostar, EXP & Material Realm Planner</h1>', 1)
h = h.replace('<p>Enter your account values, choose your season-end time and target, and the planner handles score, EXP, materials and Realm safety automatically.</p>', '<p>Plan Season 2 and beyond with cumulative Primostars, EXP, materials and Realm safety. Each season restarts progression scoring from the same Lv100 / relic +10 baseline.</p>', 1)

goal_card = '''<section class="card">
 <div class="cardhead"><h2>2. Season progression</h2><span class="chip" id="goalChip">Season 2 · set a goal</span></div>
 <div class="cardbody">
  <div class="notice" style="margin-bottom:12px">
   <b>Primostars carry between seasons.</b> Enter what you already own and the total you want to reach. The planner works out only what this season needs to contribute.
  </div>
  <div class="grid2">
   <div class="field"><label>Season</label><input id="seasonNumber" type="number" step="1" min="1" value="2"></div>
   <div class="field"><label>Season progression baseline</label><input id="seasonFloorSummary" readonly></div>
  </div>
  <div class="grid3" style="margin-top:10px">
   <div class="field"><label>Primostars you have now</label><input id="oldPrimostars" type="number" step="1" min="0" value="" placeholder="Current total"></div>
   <div class="field"><label>Total Primostar goal</label><input id="goalAwarded" type="number" step="1" min="0" value="" placeholder="Goal total"></div>
   <div class="field"><label>Still needed this season</label><input id="primostarsNeeded" readonly></div>
  </div>
  <div class="field" style="margin-top:10px"><label>Progression score required this season</label><input id="requiredScore" readonly></div>
  <p class="simple-note" id="seasonRuleNote">Only progress above the fixed seasonal baseline contributes to this season's score.</p>
  <details>
   <summary>Advanced scoring constants</summary>
   <div class="grid4" style="margin-top:9px">
    <div class="field"><label>Character / Gear / Skill / Fantomon baseline</label><input id="floor" type="number" value="100" readonly></div>
    <div class="field"><label>Relic baseline</label><input id="relicFloor" type="number" value="10" readonly></div>
    <div class="field"><label>Score / Primostar</label><input id="scorePerStar" type="number" value="100"></div>
    <div class="field"><label>Fixed season Primostars</label><input id="fixedStars" type="number" value="10"></div>
    <div class="field"><label>Character weight</label><input id="charW" type="number" value="100"></div>
    <div class="field"><label>Gear weight</label><input id="gearW" type="number" value="38"></div>
    <div class="field"><label>Skill weight</label><input id="skillW" type="number" value="13"></div>
    <div class="field"><label>Fantomon weight</label><input id="fantW" type="number" value="14"></div>
    <div class="field"><label>Relic weight</label><input id="relicW" type="number" value="57"></div>
   </div>
   <p class="subtle" style="margin-top:9px">At the start of every season, progression scoring resets to the same baseline: Character Lv100, all 5 Gear pieces Lv100, all Skills Lv100, Fantomons Lv100, and Relics +10. Your Primostar total carries forward.</p>
  </details>
 </div>
</section>'''
pat = re.compile(r'<section class="card">\s*<div class="cardhead"><h2>2\. Primostar target</h2>.*?</section>', re.S)
h, n = pat.subn(goal_card, h, count=1)
if n != 1:
    raise SystemExit('Goal card replacement failed')

old_summary = '''  <div class="metrics">
   <div class="metric major"><div class="k">Progression score</div><div class="v" id="projectedScore">0</div><div class="s"><span class="rating" id="projectedRating">D</span></div></div>
   <div class="metric"><div class="k">Primostars from score</div><div class="v" id="scoreStars">0</div><div class="s" id="scoreStarsRaw">0.00 before round-down</div></div>
   <div class="metric"><div class="k">Fixed season Primostars</div><div class="v" id="fixedStarsDisplay">+10</div><div class="s">Added after score conversion</div></div>
   <div class="metric major"><div class="k">Final season Primostars</div><div class="v" id="seasonStars">10</div><div class="s" id="seasonStarsFormula">0 from score + 10 fixed</div></div>
   <div class="metric"><div class="k">Decimal planning total</div><div class="v" id="rawStarEquivalent">10.00</div><div class="s">score ÷ 100 + fixed bonus</div></div>
   <div class="metric"><div class="k">Target difference</div><div class="v" id="cumulativeStars">0</div><div class="s">Projected final − target</div></div>
  </div>
  <div class="notice" style="margin-top:10px"><b>Season 1 reward formula:</b> floor(Progression Score ÷ 100) <b>+ 10 fixed Primostars</b>. Example: 15,200 score = 152 from score + 10 fixed = <b>162 total</b>.</div>'''
new_summary = '''  <div class="metrics">
   <div class="metric major"><div class="k">Progression score this season</div><div class="v" id="projectedScore">0</div><div class="s">Progress above the Lv100 / relic +10 baseline</div></div>
   <div class="metric"><div class="k">Primostars from score</div><div class="v" id="scoreStars">0</div><div class="s" id="scoreStarsRaw">0.00 before round-down</div></div>
   <div class="metric"><div class="k">Fixed season Primostars</div><div class="v" id="fixedStarsDisplay">+10</div><div class="s">Added after score conversion</div></div>
   <div class="metric major"><div class="k">Primostars earned this season</div><div class="v" id="seasonStars">10</div><div class="s" id="seasonStarsFormula">0 from score + 10 fixed</div></div>
   <div class="metric major"><div class="k">Projected total Primostars</div><div class="v" id="rawStarEquivalent">10</div><div class="s">Current total + this season</div></div>
   <div class="metric"><div class="k">Target difference</div><div class="v" id="cumulativeStars">0</div><div class="s">Projected total − target total</div></div>
  </div>
  <div class="notice" style="margin-top:10px"><b>Cumulative Primostars:</b> your previous-season total carries forward. Each new season adds <b>floor(Progression Score ÷ 100) + 10 fixed</b> to that existing total.</div>'''
if old_summary not in h:
    raise SystemExit('Summary block not found')
h = h.replace(old_summary, new_summary, 1)

old_ref = '''  <div class="notice">Season 1 scoring used here: Character 100, Gear 38, Skill 13, Fantomon 14, Relic 57 per seasonal level; level floor 100 and relic floor +10. Character EXP progress is fractional: Lv.128.5 counts as 28.5 seasonal character levels = 2,850 character points. Primostar reward = floor(score ÷ 100) + 10 fixed.</div>
  <div class="notice warn" style="margin-top:8px">The target-time character score includes proportional EXP within the current level. With Save 36h EXP enabled, the last 36 natural Bed hours are reserved, but boost hours during that window still count toward the current season. Use Manual character seasonal levels if you want to reproduce a whole-level spreadsheet assumption such as exactly 28.</div>
  <p class="subtle">Public cross-check: <a href="https://eog.gg/games/sword-x-staff/tools/star-calculator/" target="_blank" rel="noopener noreferrer">Eden of Gaming Primordial Star Calculator</a>. Their <a href="https://eog.gg/games/sword-x-staff/guides/season-2-prep/" target="_blank" rel="noopener noreferrer">season preparation guide</a> specifically recommends stopping Bed EXP claims 36 hours before launch and disabling Quick Claim.</p>'''
new_ref = '''  <div class="notice">Multi-season scoring uses the same category weights: Character 100, Gear 38, Skill 13, Fantomon 14 and Relic 57 per seasonal level. Each new season resets progression scoring to Character/Gear/Skills/Fantomons Lv100 and Relics +10, while your accumulated Primostars carry forward.</div>
  <div class="notice warn" style="margin-top:8px">Character EXP progress is fractional for score. Example: projected Lv128.5 is 28.5 seasonal character levels above the Lv100 baseline, worth 2,850 character points. Relic cap unlocks still require completed whole character levels.</div>
  <p class="subtle">EXP-save cross-check: <a href="https://eog.gg/games/sword-x-staff/guides/season-2-prep/" target="_blank" rel="noopener noreferrer">Eden of Gaming season preparation guide</a>.</p>'''
if old_ref not in h:
    raise SystemExit('Reference notes block not found')
h = h.replace(old_ref, new_ref, 1)

old = 'function seasonLevels(level,floor){return Math.max(0,Number(level||0)-Number(floor||0))}'
new = '''function seasonLevels(level,floor){return Math.max(0,Number(level||0)-Number(floor||0))}
function currentSeasonNumber(){return Math.max(1,Math.floor(num("seasonNumber")||1))}
function syncSeasonRules(){
 const season=currentSeasonNumber();
 const floor=100;
 const relicFloor=10;
 $("seasonNumber").value=season;
 $("floor").value=floor;
 $("relicFloor").value=relicFloor;
 $("seasonFloorSummary").value="Every season: Lv100 · Relics +10";
 $("seasonRuleNote").innerHTML=`Season ${season} keeps your existing Primostar total, but progression scoring starts again from <b>Lv100</b> for Character, Gear, Skills and Fantomons, and <b>+10</b> for Relics.`;
 const normalIds=["gearAllCur","gearAllTar","skillAllCur","skillAllTar","fantAllCur","fantAllTar"];
 normalIds.forEach(id=>{if($(id))$(id).placeholder="Baseline 100"});
 ["relicAllCur","relicAllTar"].forEach(id=>{if($(id))$(id).placeholder="Baseline +10"});
 for(let i=0;i<5;i++){if($(`gearCur${i}`))$(`gearCur${i}`).placeholder="100";if($(`gearTar${i}`))$(`gearTar${i}`).placeholder="100";}
 for(let i=0;i<8;i++){if($(`skillCur${i}`))$(`skillCur${i}`).placeholder="100";if($(`skillTar${i}`))$(`skillTar${i}`).placeholder="100";}
 for(let i=0;i<4;i++){if($(`fantCur${i}`))$(`fantCur${i}`).placeholder="100";if($(`fantTar${i}`))$(`fantTar${i}`).placeholder="100";}
 for(let i=0;i<20;i++){if($(`relicCur${i}`))$(`relicCur${i}`).placeholder="+10";if($(`relicTar${i}`))$(`relicTar${i}`).placeholder="+10";}
 return {season,floor,relicFloor}
}'''
if old not in h:
    raise SystemExit('seasonLevels helper not found')
h = h.replace(old, new, 1)

old_goal = '''function goalScore(){
 const sp=Math.max(.000001,num("scorePerStar"));
 const fixed=Math.floor(num("fixedStars"));
 const target=Math.max(fixed,Math.ceil(num("goalAwarded")));
 return Math.max(0,(target-fixed)*sp);
}
function updateGoalUI(){}'''
new_goal = '''function primostarGoalInfo(){
 const sp=Math.max(.000001,num("scorePerStar"));
 const fixed=Math.max(0,Math.floor(num("fixedStars")));
 const old=Math.max(0,Math.floor(num("oldPrimostars")));
 const target=Math.max(0,Math.ceil(num("goalAwarded")));
 const needed=Math.max(0,target-old);
 const scoreNeeded=needed<=fixed?0:(needed-fixed)*sp;
 return {sp,fixed,old,target,needed,scoreNeeded};
}
function goalScore(){return primostarGoalInfo().scoreNeeded}
function updateGoalUI(){}'''
if old_goal not in h:
    raise SystemExit('goalScore block not found')
h = h.replace(old_goal, new_goal, 1)

old_calc_start = '''function calculate(){
 updateGoalUI();
 const T=timeCalc(),XP=xpCalc(T.xpHoursApplied);'''
new_calc_start = '''function calculate(){
 updateGoalUI();
 const seasonInfo=syncSeasonRules();
 const T=timeCalc(),XP=xpCalc(T.xpHoursApplied);'''
if old_calc_start not in h:
    raise SystemExit('calculate start not found')
h = h.replace(old_calc_start, new_calc_start, 1)

calc_pat = re.compile(r' const C=costs\(\),req=computeGearRequirement\(XP\),S=req\.sums;.*? \$\("goalChip"\)\.textContent=`\$\{fmt\(num\("goalAwarded"\)\)\} ★ target`;', re.S)
calc_new = ''' const C=costs(),req=computeGearRequirement(XP),S=req.sums;
 $("quickCharacterScore").textContent=`${fmt(S.charSL,2)} seasonal character levels × ${fmt(num("charW"),2)} = ${fmt(S.charPts,2)} character points`;
 const projected=S.charPts+S.gearPts+S.skillPts+S.fantPts+S.relicPts;
 const goal=req.goal,gap=goal-projected,sp=Math.max(.000001,num("scorePerStar")),fixed=num("fixedStars");
 const goalInfo=primostarGoalInfo();
 const scoreStarsRaw=projected/sp;
 const scoreStarsAwarded=Math.floor(scoreStarsRaw+1e-9);
 const fixedAwarded=Math.floor(fixed);
 const awarded=scoreStarsAwarded+fixedAwarded;
 const projectedTotal=goalInfo.old+awarded;
 const totalDifference=projectedTotal-goalInfo.target;
 const targetShortfall=Math.max(0,goalInfo.target-projectedTotal);
 $("projectedScore").textContent=fmt(projected,2);
 $("scoreStars").textContent=fmt(scoreStarsAwarded);
 $("scoreStarsRaw").textContent=`${fmt(scoreStarsRaw,2)} before round-down`;
 $("fixedStarsDisplay").textContent=`+${fmt(fixedAwarded)}`;
 $("seasonStars").textContent=fmt(awarded);
 $("seasonStarsFormula").textContent=`${fmt(scoreStarsAwarded)} from score + ${fmt(fixedAwarded)} fixed`;
 $("rawStarEquivalent").textContent=fmt(projectedTotal);
 $("cumulativeStars").textContent=(totalDifference>=0?"+":"")+fmt(totalDifference);
 $("primostarsNeeded").value=fmt(goalInfo.needed);
 $("requiredScore").value=fmt(Math.ceil(goal*100)/100,2);
 $("ratingChip").textContent=`Season ${seasonInfo.season} · baseline Lv100`;
 if(goalInfo.target<=goalInfo.old){
  $("goalStatus").className="notice";
  $("goalStatus").innerHTML=`<b>Target already reached.</b> You currently have ${fmt(goalInfo.old)} Primostars, which is already at or above the ${fmt(goalInfo.target)} target.`;
 }else if(targetShortfall<=0){
  $("goalStatus").className="notice";
  $("goalStatus").innerHTML=`<b>Target reached in projection.</b> ${fmt(goalInfo.old)} current + ${fmt(awarded)} earned this season = <b>${fmt(projectedTotal)} total Primostars</b>.`;
 }else{
  $("goalStatus").className="notice warn";
  $("goalStatus").innerHTML=`<b>${fmt(targetShortfall)} Primostars still short.</b> Projection: ${fmt(goalInfo.old)} current + ${fmt(awarded)} this season = ${fmt(projectedTotal)} / ${fmt(goalInfo.target)}. You still need ${fmt(Math.max(0,gap),2)} progression score toward this season's target.`;
 }
 $("goalChip").textContent=goalInfo.target?`S${seasonInfo.season} · ${fmt(goalInfo.needed)} remaining`:`Season ${seasonInfo.season} · set a goal`;'''
h, n = calc_pat.subn(calc_new, h, count=1)
if n != 1:
    raise SystemExit('Main calculation block replacement failed')

old_ids = 'const ids=["startTime","targetTime","resetTime","boostHoursPerReset","charLevel","charXp","charNeed","xpHr","xpBase100","xpIncrease","xpCurve","goalAwarded","floor","relicFloor","scorePerStar","fixedStars","charW","gearW","skillW","fantW","relicW","refreshSystem","hammerNow","goldNow","gloveNow","shovelNow","gearAllCur","gearAllTar","skillAllCur","skillAllTar","fantAllCur","fantAllTar","relicAllCur","relicAllTar"];'
new_ids = 'const ids=["startTime","targetTime","resetTime","boostHoursPerReset","charLevel","charXp","charNeed","xpHr","xpBase100","xpIncrease","xpCurve","seasonNumber","oldPrimostars","goalAwarded","floor","relicFloor","scorePerStar","fixedStars","charW","gearW","skillW","fantW","relicW","refreshSystem","hammerNow","goldNow","gloveNow","shovelNow","gearAllCur","gearAllTar","skillAllCur","skillAllTar","fantAllCur","fantAllTar","relicAllCur","relicAllTar"];'
if old_ids not in h:
    raise SystemExit('state ids not found')
h = h.replace(old_ids, new_ids, 1)
h = h.replace('return {v:24,values:v,core:JSON.parse(JSON.stringify(core))}', 'return {v:27,values:v,core:JSON.parse(JSON.stringify(core))}', 1)
h = h.replace('localStorage.setItem("sxsPlannerV24"', 'localStorage.setItem("sxsPlannerV27"', 1)
h = h.replace('a.download="sword-x-staff-plan-v24.json"', 'a.download="sword-x-staff-plan-v27.json"', 1)
h = h.replace('localStorage.removeItem("sxsPlannerV24")', 'localStorage.removeItem("sxsPlannerV27")', 1)

old_tail = ''' if(s.core)for(const k of Object.keys(core))if(s.core[k])Object.assign(core[k],s.core[k]);
 renderCore();calculate()
}'''
new_tail = ''' if(s.core)for(const k of Object.keys(core))if(s.core[k])Object.assign(core[k],s.core[k]);
 if((Number(s.v)||0)<25){
  $("goalAwarded").value="";
  $("oldPrimostars").value="";
 }
 renderCore();calculate()
}'''
if old_tail not in h:
    raise SystemExit('applyState tail not found')
h = h.replace(old_tail, new_tail, 1)

old_loader = '''const saved=localStorage.getItem("sxsPlannerV24");
if(saved){
 try{applyState(JSON.parse(saved));}
 catch(e){console.error(e);calculate()}
}else calculate();'''
new_loader = '''const saved=localStorage.getItem("sxsPlannerV27")||localStorage.getItem("sxsPlannerV24");
if(saved){
 try{
  const parsed=JSON.parse(saved);
  applyState(parsed);
  if(!localStorage.getItem("sxsPlannerV27"))save(true);
 }catch(e){console.error(e);calculate()}
}else calculate();'''
if old_loader not in h:
    raise SystemExit('loader not found')
h = h.replace(old_loader, new_loader, 1)

h = h.replace('Fan-made planner. Cyan fields are yours to edit; gray fields are calculated. Relic planned levels are automatically limited by projected character level.', 'Fan-made multi-season planner. Cyan fields are yours to edit; gray fields are calculated. Primostars are cumulative across seasons, while Character, Gear, Skills and Fantomons reset to the Lv100 scoring baseline and Relics reset to +10 each season. Relic planned levels are automatically limited by projected character level.', 1)

old_rr = '''function renderRatings(){
 $("ratingGrid").innerHTML=ratings.map(r=>`<div class="rpill" data-r="${r.name}"><b>${r.name}</b><br>${fmt(r.min)}${isFinite(r.max)?"–"+fmt(r.max):"+"}</div>`).join("")
}'''
new_rr = '''function renderRatings(){
 const el=$("ratingGrid");
 if(el)el.innerHTML=ratings.map(r=>`<div class="rpill" data-r="${r.name}"><b>${r.name}</b><br>${fmt(r.min)}${isFinite(r.max)?"–"+fmt(r.max):"+"}</div>`).join("")
}'''
if old_rr in h:
    h = h.replace(old_rr, new_rr, 1)

checks = [
    'Multi-Season Primostar & Realm Planner v27',
    'id="oldPrimostars"',
    'id="primostarsNeeded"',
    'id="seasonNumber"',
    'const floor=100;',
    'const relicFloor=10;',
    'all 5 Gear pieces Lv100',
    'localStorage.setItem("sxsPlannerV27"',
    'function primostarGoalInfo()',
    'function syncSeasonRules()'
]
missing = [x for x in checks if x not in h]
if missing:
    raise SystemExit(f'Validation failed: {missing}')
if 'floors advance automatically' in h:
    raise SystemExit('Old advancing-floor wording remains')

p.write_text(h, encoding='utf-8')
print('Updated calculator to v27')
