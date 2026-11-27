chrome.runtime.onInstalled.addListener(()=>chrome.storage.session.clear());
// A normal extension window survives native file pickers. Bind it to the source
// tab before creating the companion; its own tab must never become the fill target.
chrome.action.onClicked.addListener(tab=>{
 if(!Number.isInteger(tab.id))return;
 chrome.windows.create({url:chrome.runtime.getURL('popup.html')+'?tab='+tab.id,type:'popup',width:440,height:800});
});
