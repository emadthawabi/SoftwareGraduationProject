'use strict';
buildShell();
window.addEventListener('hashchange',()=>{window.__keepScroll=false;renderPage();window.scrollTo(0,0);window.__keepScroll=true});
renderPage();
