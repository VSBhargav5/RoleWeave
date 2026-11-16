/* In-memory per-proposal edit history; no storage, request or credential handling. */
export class ReviewHistory {
 constructor(initial,limit=20){if(!Number.isInteger(limit)||limit<2||limit>50)throw Error('Invalid edit-history bound');this.limit=limit;this.states=[structuredClone(initial)];this.index=0}
 record(state){if(JSON.stringify(state)===JSON.stringify(this.states[this.index]))return;this.states=this.states.slice(0,this.index+1);this.states.push(structuredClone(state));if(this.states.length>this.limit)this.states.shift();this.index=this.states.length-1}
 get canUndo(){return this.index>0}
 get canRedo(){return this.index+1<this.states.length}
 undo(){if(this.canUndo)this.index--;return structuredClone(this.states[this.index])}
 redo(){if(this.canRedo)this.index++;return structuredClone(this.states[this.index])}
 clear(){this.states=[];this.index=-1}
}
