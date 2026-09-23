const assert = require('node:assert/strict');
const {test}=require('node:test');
const {trainingElapsed}=require('../training_dashboard/time_axis.js');
test('continuous time removes a two-day pause and preserves within-session timing',()=>{
  const sessions=[{time:100,end:200},{time:173000,end:173100}];
  assert.equal(trainingElapsed(sessions,150),50);
  assert.equal(trainingElapsed(sessions,200),100);
  assert.equal(trainingElapsed(sessions,173000),100);
  assert.equal(trainingElapsed(sessions,173050),150);
  assert.equal(trainingElapsed(sessions,174000),200);
});
test('current-session time can begin at zero without changing original timestamps',()=>{
  const sessions=[{time:100,end:200},{time:300,end:400}];
  const before=JSON.stringify(sessions);
  assert.equal(trainingElapsed(sessions,350)-trainingElapsed(sessions,300),50);
  assert.equal(JSON.stringify(sessions),before);
  assert.equal(trainingElapsed([],10),0);
});
