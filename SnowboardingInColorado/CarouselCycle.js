const track = document.querySelector('.carousel-track');
const items = Array.from(document.querySelectorAll('.carousel-item'));

// Clone the first and last items
const firstItemClone = items[0].cloneNode(true);
const lastItemClone = items[items.length - 1].cloneNode(true);

// Append the clones to the beginning and end of the carousel track
track.appendChild(firstItemClone);
track.insertBefore(lastItemClone, items[0]);

const itemWidth = items[0].getBoundingClientRect().width;
let counter = 1; // Start from the first cloned item

function nextSlide() {
   counter++;
   moveSlide();
}

function prevSlide() {
   counter--;
   moveSlide();
}

function moveSlide() {
   const offset = -itemWidth * counter;
   track.style.transform = `translateX(${offset}px)`;

   // If reaching the last clone, reset counter to 1
   if (counter >= items.length - 1) {
      setTimeout(() => {
         track.style.transition = 'none';
         track.style.transform = `translateX(${-itemWidth}px)`;
         counter = 1;
         setTimeout(() => {
            track.style.transition = 'transform 0.5s ease';
         });
      }, 500); // Wait for the transition to complete before resetting
   }
   // If reaching the first clone, reset counter to the last real item
   else if (counter <= 0) {
      setTimeout(() => {
         track.style.transition = 'none';
         track.style.transform = `translateX(${-itemWidth * (items.length - 2)}px)`;
         counter = items.length - 2;
         setTimeout(() => {
            track.style.transition = 'transform 0.5s ease';
         });
      }, 500); // Wait for the transition to complete before resetting
   }
}
