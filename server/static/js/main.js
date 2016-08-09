window.paceOptions = {
  startOnPageLoad: false,
  ajax: true,
  document: false, // disabled
  eventLag: false // disabled
};

if (typeof HTMLElement.prototype.removeClass !== "function") {
    HTMLElement.prototype.removeClass = function(remove) {
        var newClassName = "";
        var i;
        var classes = this.className.split(" ");
        for(i = 0; i < classes.length; i++) {
            if(classes[i] !== remove) {
                newClassName += classes[i] + " ";
            }
        }
        this.className = newClassName;
    }
}
