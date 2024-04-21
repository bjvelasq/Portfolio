document.addEventListener('DOMContentLoaded', function() {
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const images = document.querySelectorAll('.image-container .image');
    let currentIndex = 0;

    prevBtn.addEventListener('click', function() {
        currentIndex--;
        if (currentIndex < 0) {
            currentIndex = images.length - 1;
        }
        shuffleImages();
        showCaption(); // Call showCaption after shuffling images
    });

    nextBtn.addEventListener('click', function() {
        currentIndex++;
        if (currentIndex >= images.length) {
            currentIndex = 0;
        }
        shuffleImages();
        showCaption(); // Call showCaption after shuffling images
    });

    function shuffleImages() {
        images.forEach((image, index) => {
            let zIndex = (index === currentIndex) ? 1 : 0;
            image.style.zIndex = zIndex;
        });
    }

    // Show caption when image is at front
    function showCaption() {
        images.forEach((image, index) => {
            if (index === currentIndex) {
                image.querySelector('.image-caption').style.opacity = 1;
            } else {
                image.querySelector('.image-caption').style.opacity = 0;
            }
        });
    }

    // Call the functions initially to set the initial state
    shuffleImages();
    showCaption();
});
document.addEventListener('DOMContentLoaded', function() {
    const pollForm = document.getElementById('poll-form');
    const resultsList = document.getElementById('results-list');

    // Initialize votes object
    let votes = {
        Keystone: 0,
        "A-Basin": 0,
        "Copper Mountain": 0,
        Breckenridge: 0
    };

    // Display initial poll results
    displayResults();

    // Handle form submission
    pollForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const selectedResort = document.querySelector('input[name="resort"]:checked');
        if (selectedResort) {
            const resortName = selectedResort.value;
            votes[resortName]++;
            displayResults();
            pollForm.reset();
        } else {
            alert('Please select a resort.');
        }
    });

    // Function to display poll results
    function displayResults() {
        // Clear previous results
        resultsList.innerHTML = '';

        // Calculate total votes
        const totalVotes = Object.values(votes).reduce((total, current) => total + current, 0);

        // Display updated results as percentages
        for (const resort in votes) {
            const percentage = totalVotes === 0 ? 0 : ((votes[resort] / totalVotes) * 100).toFixed(2);
            const listItem = document.createElement('li');
            listItem.textContent = `${resort}: ${percentage}%`;
            resultsList.appendChild(listItem);
        }
    }
});
