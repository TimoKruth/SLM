'use strict';
// Estimated elapsed time within logged sessions; excludes gaps between sessions.
function trainingElapsed(sessions, time) {
  let total=0;
  for(const session of sessions){
    if(time<session.time)break;
    total+=Math.max(0,Math.min(time,session.end)-session.time);
    if(time<=session.end)break;
  }
  return total;
}
if(typeof module!=='undefined' && module.exports)module.exports={trainingElapsed};
