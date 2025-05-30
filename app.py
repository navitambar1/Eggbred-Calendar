from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import calendar
from datetime import datetime, date
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# MySQL Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'eggbred$newdb'
}

CATEGORY_COLORS = {
    'work': '#ffc107',
    'personal': '#28a745',
    'holiday': '#17a2b8',
    'birthday': '#dc3545'
}

def get_db_connection():
    """Create and return a connection to the MySQL database"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

def init_db():
    """Initialize the database tables if they don't exist"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    color VARCHAR(7) NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS event_dates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    event_id INT NOT NULL,
                    event_date DATE NOT NULL,
                    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS legend (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    label VARCHAR(255) NOT NULL,
                    color VARCHAR(7) NOT NULL
                )
            ''')
            seed_default_legends()
            connection.commit()
        except Error as e:
            print(f"Error initializing database: {e}")
        finally:
            cursor.close()
            connection.close()

DEFAULT_LEGENDS = [
    ("Category 1", "#ffc107"),
    ("Category 2", "#28a745"),
    ("Category 3", "#17a2b8"),
    ("Category 4", "#dc3545"),
    ("Category 5", "#007bff"),
    ("Category 6", "#6610f2"),
    ("Category 7", "#fd7e14"),
    ("Category 8", "#20c997"),
]
def seed_default_legends():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM legend")
    count = cursor.fetchone()[0]
    if count == 0:
        for label, color in DEFAULT_LEGENDS:
            cursor.execute("INSERT INTO legend (label, color) VALUES (%s, %s)", (label, color))
        connection.commit()
    cursor.close()
    connection.close()
    
init_db()
# seed_default_legends()

def group_dates(dates):
    """Group consecutive dates together"""
    dates = sorted(dates)
    grouped = []
    if not dates:
        return grouped
    
    start = end = dates[0]
    for current in dates[1:]:
        if (current - end).days == 1:
            end = current
        else:
            grouped.append((start, end))
            start = end = current
    grouped.append((start, end))
    return grouped

def get_legend():
    connection = get_db_connection()
    legend_data = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Make sure to select the id field for editing
            cursor.execute("SELECT id, label, color FROM legend ORDER BY id")
            legend_data = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching legend data: {e}")
        finally:
            cursor.close()
            connection.close()
    return legend_data


def get_all_events(year=None):
    """Get all events from the database with optional year filter"""
    events = []
    connection = get_db_connection()
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            if year:
                query = '''
                    SELECT e.id, e.title, e.color, ed.event_date
                    FROM events e
                    JOIN event_dates ed ON e.id = ed.event_id
                    WHERE YEAR(ed.event_date) = %s
                    ORDER BY ed.event_date
                '''
                cursor.execute(query, (year,))
            else:
                query = '''
                    SELECT e.id, e.title, e.color, ed.event_date
                    FROM events e
                    JOIN event_dates ed ON e.id = ed.event_id
                    ORDER BY ed.event_date
                '''
                cursor.execute(query)
            rows = cursor.fetchall()
            event_dict = {}
            for row in rows:
                event_id = row['id']
                event_date = row['event_date']
                if event_id not in event_dict:
                    event_dict[event_id] = {
                        'id': event_id,
                        'title': row['title'],
                        'color': row['color'],
                        'dates': []
                    }
                event_dict[event_id]['dates'].append(event_date)
            events = list(event_dict.values())
        except Error as e:
            print(f"Error fetching events: {e}")
        finally:
            cursor.close()
            connection.close()
    return events

def add_or_update_legend(label, color):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            # Try update first
            cursor.execute("""
                INSERT INTO legend (label, color)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE color = VALUES(color)
            """, (label, color))
            connection.commit()
        finally:
            cursor.close()
            connection.close()


def add_event_to_db(title, color, dates):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO events (title, color) VALUES (%s, %s)",
                (title, color)
            )
            event_id = cursor.lastrowid
            for event_date in dates:
                cursor.execute(
                    "INSERT INTO event_dates (event_id, event_date) VALUES (%s, %s)",
                    (event_id, event_date)
                )
            connection.commit()
            return True
        except Error as e:
            print(f"Error adding event: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()
    return False

def clean_date_string(date_str):
    try:
        return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z").date().isoformat()
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date().isoformat()
        except ValueError:
            raise ValueError(f"Unrecognized date format: {date_str}")

def update_event_in_db(event_id, title, color, dates):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE events SET title = %s, color = %s WHERE id = %s",
                (title, color, event_id)
            )
            cursor.execute("DELETE FROM event_dates WHERE event_id = %s", (event_id,))
            for date in dates:
                cleaned_date = clean_date_string(date)
                cursor.execute(
                    "INSERT INTO event_dates (event_id, event_date) VALUES (%s, %s)",
                    (event_id, cleaned_date)
                )
            connection.commit()
            return True
        except Error as e:
            print(f"Error updating event: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()
    return False

@app.route('/get_legend')
def get_legend_route():
    try:
        return jsonify(get_legend())
    except Exception as e:
        return jsonify({'error': f'Failed to fetch legend: {str(e)}'}), 500

@app.route('/update_legend', methods=['POST'])
def update_legend():
    try:
        data = request.get_json()
        legend_id = data.get('id')
        new_label = data.get('label')
        
        # Validate input
        if not legend_id or not new_label:
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        # Sanitize the label (trim whitespace, limit length)
        new_label = new_label.strip()[:100]  # Limit to 100 characters
        
        if not new_label:
            return jsonify({'success': False, 'error': 'Label cannot be empty'})
        
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                
                # Update the legend item
                update_query = "UPDATE legend SET label = %s WHERE id = %s"
                cursor.execute(update_query, (new_label, legend_id))
                
                # Check if any rows were affected
                if cursor.rowcount == 0:
                    return jsonify({'success': False, 'error': 'Legend item not found'})
                
                connection.commit()
                return jsonify({'success': True, 'message': 'Legend updated successfully'})
                
            except Exception as e:
                connection.rollback()
                return jsonify({'success': False, 'error': f'Database error: {str(e)}'})
            finally:
                cursor.close()
                connection.close()
        else:
            return jsonify({'success': False, 'error': 'Database connection failed'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})


def delete_event_from_db(event_id):
    """Delete an event from the database"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
            
            connection.commit()
            return True
        except Error as e:
            print(f"Error deleting event: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()
    return False

@app.route('/', methods=['GET'])
def index():
    year = request.args.get('year', default=datetime.now().year, type=int)
    months = []
    for month in range(1, 13):
        month_name = calendar.month_name[month]
        cal = calendar.Calendar(firstweekday=6)  
        weeks = list(cal.itermonthdays(year, month))
        weeks_grouped = [weeks[i:i+7] for i in range(0, len(weeks), 7)]
        months.append({'name': month_name, 'month': month, 'weeks': weeks_grouped})
    events = get_all_events(year)
    event_map = {}
    for event in events:
        for d in event['dates']:
            event_map[d] = event
    return render_template('index.html', year=year, months=months, event_map=event_map, category_colors=CATEGORY_COLORS, grouped_events=events, date=date, events=events)

@app.route('/readonly', methods=['GET'])
def readOnly():
    year = request.args.get('year', default=datetime.now().year, type=int)
    months = []
    for month in range(1, 13):
        month_name = calendar.month_name[month]
        cal = calendar.Calendar(firstweekday=6)  
        weeks = list(cal.itermonthdays(year, month))
        weeks_grouped = [weeks[i:i+7] for i in range(0, len(weeks), 7)]
        months.append({'name': month_name, 'month': month, 'weeks': weeks_grouped})
    events = get_all_events(year)
    event_map = {}
    for event in events:
        for d in event['dates']:
            event_map[d] = event
    return render_template('readOnly.html', year=year, months=months, event_map=event_map, category_colors=CATEGORY_COLORS, grouped_events=events, date=date, events=events)


@app.route('/add_event', methods=['POST'])
def add_event():
    dates_str = request.form.get('dates')
    title = request.form.get('title')
    color = request.form.get('color')
    if not dates_str or not title or not color:
        return redirect(url_for('index'))
    selected_dates = []
    for dt in dates_str.split(','):
        dt = dt.strip()
        try:
            parsed_date = datetime.strptime(dt, '%Y-%m-%d').date()
            selected_dates.append(parsed_date)
        except ValueError:
            continue
    if selected_dates:
        add_event_to_db(title, color, selected_dates)
        return redirect(url_for('index', year=selected_dates[0].year))
    return redirect(url_for('index'))

@app.route('/update_event', methods=['POST'])
def update_event():
    event_id = request.form.get('event_id')
    title = request.form.get('title')
    color = request.form.get('color')
    dates_json = request.form.get('dates')

    try:
        dates = json.loads(dates_json)
    except json.JSONDecodeError:
        dates = []

    if update_event_in_db(event_id, title, color, dates):
        return redirect(url_for('index', year=datetime.now().year))
    return redirect(url_for('index'))

@app.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    delete_event_from_db(event_id)
    return ('', 204)  # No content response

if __name__ == '__main__':
    app.run(debug=True)