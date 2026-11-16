import test from 'node:test';
import assert from 'node:assert/strict';
import {ReviewHistory} from '../web/review-history.mjs';

test('Undo/redo preserves independent wording and selected-control snapshots',()=>{const h=new ReviewHistory({wording:'Proposal',selected:false});h.record({wording:'Corrected project',selected:true});assert.deepEqual(h.undo(),{wording:'Proposal',selected:false});assert.deepEqual(h.redo(),{wording:'Corrected project',selected:true})});
test('Editing after undo discards the abandoned redo branch',()=>{const h=new ReviewHistory('proposal');h.record('first');h.record('second');h.undo();h.record('alternative');assert.equal(h.canRedo,false);assert.equal(h.undo(),'first');assert.equal(h.redo(),'alternative')});
test('Repeated identical controls add no step and state copies cannot mutate history',()=>{const initial={text:'proposal'},h=new ReviewHistory(initial);initial.text='external';h.record({text:'proposal'});assert.equal(h.canUndo,false);const current=h.undo();current.text='external';assert.equal(h.redo().text,'proposal');const edit={text:'edit'};h.record(edit);edit.text='external';assert.equal(h.redo().text,'edit')});
test('Bounded history evicts oldest edits and never invents extra undo steps',()=>{const h=new ReviewHistory(0,3);for(let i=1;i<8;i++)h.record(i);assert.equal(h.states.length,3);assert.equal(h.undo(),6);assert.equal(h.undo(),5);assert.equal(h.canUndo,false);assert.equal(h.undo(),5);assert.equal(h.redo(),6)});
test('A separate proposal resets history and close clears retained wording',()=>{const old=new ReviewHistory('old');old.record('edit');const next=new ReviewHistory('new proposal');assert.equal(next.canUndo,false);old.clear();assert.equal(old.states.length,0);assert.equal(old.canRedo,false)});
