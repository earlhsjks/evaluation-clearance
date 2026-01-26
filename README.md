# Evaluation Clearance System
<!-- [![Ask DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/earlhsjks/evaluation-clearance) -->

A web application built with Flask to verify student evaluation clearance status. It synchronizes data from a Google Spreadsheet into a MySQL database and provides a simple, real-time search interface for administrators or staff. The frontend is designed for a fast, responsive user experience with debounced search and automatic data refresh capabilities.

## Key Features

*   **Student Search:** Look up students by their School ID or full name.
*   **Real-time Status:** Instantly see if a student is "Cleared" or "Not Found".
*   **Google Sheets Integration:** Automatically imports and synchronizes student lists from a public Google Sheet CSV link.
*   **Dynamic Refresh:** Includes a manual refresh button and an automatic background refresh job that runs every hour to keep data current.
*   **Responsive UI:** A clean, mobile-friendly interface built with Bootstrap for easy access on any device.
*   **Live Updates:** Uses WebSockets (Flask-SocketIO) to notify connected clients when student data is updated.
*   **Efficient Searching:** The search input is debounced to prevent excessive API calls while the user is typing.

## Technology Stack

*   **Backend:** Flask, Flask-SQLAlchemy, Flask-SocketIO, Waitress, APScheduler
*   **Database:** MySQL
*   **Frontend:** HTML, CSS, JavaScript, Bootstrap, Font Awesome
*   **Data Handling:** Pandas, Requests

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.x
*   A running MySQL server
*   A Google Sheet with student data

### Installation & Setup

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/earlhsjks/evaluation-clearance.git
    cd evaluation-clearance
    ```

2.  **Create and activate a virtual environment:**
    ```sh
    # For Windows
    python -m venv venv
    venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```sh
    pip install -r req.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the root directory and populate it with your database credentials and a secret key.

    ```env
    SECRET_KEY='your_strong_secret_key'
    DB_HOST='localhost'
    DB_USER='your_db_user'
    DB_PASS='your_db_password'
    DB_NAME='your_db_name'
    ```

5.  **Set up the Database:**
    *   Connect to your MySQL server and create the database specified in your `.env` file.
    *   The application will create the necessary `students` and `settings` tables on its first run, based on the models in `models/models.py`.

6.  **Configure the Google Sheet:**
    *   Prepare a Google Sheet with two columns: `School ID Number` and `Name (Ex. Juan S. Dela Cruz)`.
    *   Publish the sheet to the web as a CSV file (`File > Share > Publish to web > CSV`). Copy the generated link.
    *   Insert this link into your `settings` table. You can do this by connecting to your database and running the following SQL command:
    ```sql
    INSERT INTO settings (`key`, `value`) VALUES ('spreadsheet_link', 'YOUR_GOOGLE_SHEET_CSV_LINK_HERE');
    ```

7.  **Run the application:**
    ```sh
    python app.py
    ```
    The application will be accessible at `http://127.0.0.1:5005`.

## Usage

Once the application is running, open your web browser and navigate to `http://127.0.0.1:5005`.

*   **Search**: Use the search bar to enter a student's School ID or name. The system will automatically search as you type.
*   **Refresh Data**: Click the "Refresh" button to manually trigger a synchronization with the configured Google Sheet. Data also refreshes automatically in the background.

## API Endpoints

The application exposes a few simple API endpoints for its functionality:

*   `POST /api/check`: Searches for a student.
    *   **Body**: `{ "search_by": "id|name", "query": "search_term" }`
    *   **Response**: JSON object with student clearance status and data.
*   `POST /api/refresh`: Manually triggers a data refresh from the Google Sheet.
    *   **Response**: JSON object indicating success or failure.
*   `POST /api/save_response`: An endpoint for saving survey responses (currently not fully utilized by the frontend).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
