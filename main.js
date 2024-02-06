const scroller = querySelectorAll(".scroller");

if (!window.matchMedia("(prefers-reduced-motion:reduce)").matches){
    addAnimation();
}

function addAnimation() {
    scroller.forEach(scroller => {
        scroller.setAttribute("data-animated", true);
    });
}