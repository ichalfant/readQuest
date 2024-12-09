# Read Quest

## Overview
The Reading Tracker is a Flask-based web application that allows users to manage their reading goals and track their progress. Users can log in to view their personal dashboard, which displays their in-progress reads and a progress bar for their yearly reading goal. Additionally, users can manage their personal library of books, track statistics related to their reading habits, and perform CRUD operations on their books.

## Features

### User Features
- **User Authentication**:
  - Users can register, log in, and log out securely.
- **Dashboard**:
  - View in-progress reads.
  - Track yearly reading goal progress with a visual progress bar.
- **Library Management**:
  - View all books in the library, sorted by their status (e.g., In Progress, Completed, Want to Read).
  - Add new books to the library.
  - Edit book details from the dashboard or the library page.
  - Delete books from the library.
- **Statistics Page**:
  - View monthly statistics, such as total books read, pages read, and other insights.

## Technologies
- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript (for interactive elements)

## File Structure
readQuest/
|--static/
|  |--cover_images/
|  |--css/
|  |--js/
|  |--uploads/
|--templates/
|--app.py
|--database.py
|--requirements.txt
