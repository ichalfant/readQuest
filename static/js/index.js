let currentGoal = null;
document.addEventListener('DOMContentLoaded', function () {
    fetchGoal();
    updateProgressBar();
});

    /*
    var editBookModal = document.getElementById('editBookModal');
    var bookTitleElem = document.getElementById('bookTitle');
    var bookStatusElem = document.getElementById('bookStatus');
    var bookFormatElem = document.getElementById('bookFormat');
    var updateBookForm = document.getElementById('updateBookForm');
    var deleteBookButton = document.getElementById('deleteBookButton');

    var startDateGroup = document.getElementById('startDateGroup');
    var endDateGroup = document.getElementById('endDateGroup');
    var dropDateGroup = document.getElementById('dropDateGroup');
    var addedToReadDateGroup = document.getElementById('addedToReadDateGroup');

    var selectedReadingInstanceId;
    */

    /*
    function updateDateFields() {
        var selectedStatus = bookStatusElem.value;
        console.log("Update Date Fields Called with Status:", selectedStatus);

        // Hide all date fields initially
        startDateGroup.style.display = 'none';
        endDateGroup.style.display = 'none';
        dropDateGroup.style.display = 'none';
        addedToReadDateGroup.style.display = 'none';

        // show the relevant date fields based on the selected status
        if (selectedStatus === 'in progress') {
            startDateGroup.style.display = 'block';
        } else if (selectedStatus === 'completed') {
            startDateGroup.style.display = 'block';
            endDateGroup.style.display = 'block';
        } else if (selectedStatus === 'dropped') {
            startDateGroup.style.display = 'block';
            dropDateGroup.style.display = 'block';
        } else if (selectedStatus === 'to read') {
            addedToReadDateGroup.style.display = 'block';
        }
    }
        */
    /*
    
    document.querySelectorAll('.edit-book').forEach(function (link) {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            var ReadingInstanceId = link.getAttribute('data-reading-instance-id');
            var title = link.getAttribute('data-title');
            var status = link.getAttribute('data-status');
            var format = link.getAttribute('data-format');

            var start_date = link.getAttribute('data-start-date');
            var end_date = link.getAttribute('data-end-date');
            var drop_date = link.getAttribute('data-drop-date');
            var added_to_read_date = link.getAttribute('data-added-to-read-date');

            selectedReadingInstanceId = ReadingInstanceId;
            bookTitleElem.textContent = title;
            bookStatusElem.value = status;
            bookFormatElem.value = format;

            document.getElementById('start_date').value = start_date || "";
            document.getElementById('end_date').value = end_date || "";
            document.getElementById('drop_date').value = drop_date || "";
            document.getElementById('added_to_read_date').value = added_to_read_date || "";

            updateDateFields();
            
            $(editBookModal).modal('show');
        });   
    });
    */

    /*
    updateBookForm.addEventListener('submit', function (event) {
        event.preventDefault();

        var updatedStatus = bookStatusElem.value;
        var updatedFormat = bookFormatElem.value;
        var updatedStartDate = document.getElementById('start_date').value;
        var updatedEndDate = document.getElementById('end_date').value;
        var updatedDropDate = document.getElementById('drop_date').value;
        var updatedAddedToReadDate = document.getElementById('added_to_read_date').value;

        fetch(`/update-reading-instance/${selectedReadingInstanceId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                'status': updatedStatus,
                'format': updatedFormat,
                'start_date': updatedStartDate,
                'end_date': updatedEndDate,
                'drop_date': updatedDropDate,
                'added_to_read_date': updatedAddedToReadDate
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Book updated successfully');
                location.reload();
                fetchGoal();
                updateProgressBar();
            } else {
                alert('Error updating book: ' + data.message);
            }
            $(editBookModal).modal('hide');
        })
        .catch(error => {
            console.error('Error:', error);
        });
    });
    */

    /*
    if (deleteBookButton) {
        deleteBookButton.addEventListener('click', function () {
            if (!confirm('Are you sure you want to delete this book?')) {
                return;
            }

            fetch(`/delete-reading-instance/${selectedReadingInstanceId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Book deleted successfully');
                    location.reload();
                    fetchGoal();
                    updateProgressBar();
                } else {
                    alert('Error deleting book: ' + data.message);
                }
                $(editBookModal).modal('hide');
            })
            .catch(error => {
                console.error('Error:', error);
            });
        })
    }
});
*/

function fetchGoal() {
    fetch("/api/goal")
        .then(response => response.json())
        .then(data => {
            currentGoal = data.goal;
            displayGoal();
        })
        .catch(error => {
            console.error('Error fetching goal:', error);
        });
}

function displayGoal() {
    const goalContainer = document.getElementById('goal-container');
    goalContainer.innerHTML = "";

    if (currentGoal === null) {
        goalContainer.innerHTML = `
            <p>You have not set a goal for this year.</p>
            <button onclick="showGoalForm()">Create Goal</button>
        `;
    } else {
        goalContainer.innerHTML = `
            <p>Your goal is to read ${currentGoal} books this year.</p>
            <div class="progress" style="margin-top: 20px;">
                <div id="progressBar" class="progress-bar" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="${currentGoal}"></div>
            </div>
            <p id="progressText">0 out of ${currentGoal}</p>
            <button onclick="showGoalForm(${currentGoal})">Edit Goal</button>
        `;

        updateProgressBar();
    }
}

function updateProgressBar() {
    fetch('/api/finished_books')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const finishedCount = data.finished_count;
                const progressBar = document.getElementById('progressBar');
                const progressText = document.getElementById('progressText');

                const percentage = (finishedCount / currentGoal) * 100;
                progressBar.style.width = percentage + '%';
                progressText.textContent = `You have read ${finishedCount} out of ${currentGoal} books.`;
            }
        })
        .catch(error => {
            console.error('Error fetching finished books:', error);
        });
}
function showGoalForm(goal = "") {
    const goalContainer = document.getElementById('goal-container');
    goalContainer.innerHTML = `
        <form id="goalForm" onsubmit="submitGoal(event)">
            <label for="goalInput">Set a reading goal (number of books):</label>
            <input type="number" id="goalInput" min="1" value="${goal}" required>
            <button type="submit">Submit</button>
            <button type="button" onclick="displayGoal()">Cancel</button>
        </form>
    `;
}

function submitGoal(event) {
    event.preventDefault();
    const goalInput = document.getElementById('goalInput');
    const newGoal = parseInt(goalInput.value);

    if(isNaN(newGoal) || newGoal < 1) {
        alert("Please enter a valid number of books.");
        return;
    }

    fetch("/api/goal", {
        method: "POST",
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            'goal': newGoal
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw new Error(err.message);});
        }
        return response.json();
    })
    .then(data => {
        currentGoal = data.goal;
        displayGoal();
    })
    .catch(error => {
        alert("An error occurred while updating the goal. Please try again.");
        console.error('Error updating goal:', error);
    });
}
