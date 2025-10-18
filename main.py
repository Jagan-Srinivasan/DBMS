import sqlite3
import threading
import time
import random
from flask import Flask, render_template, request, redirect, url_for, jsonify
from contextlib import contextmanager

app = Flask(__name__)
app.secret_key = 'payroll_management_secret_key'

DATABASE = 'payroll.db'
NODE1_DB = 'node1_dept.db'
NODE2_DB = 'node2_emp.db'
NODE3_DB = 'node3_salary.db'
NODE4_DB = 'node4_work.db'

concurrency_log = []

@contextmanager
def get_db_connection(db_name=DATABASE):
    conn = sqlite3.connect(db_name, check_same_thread=False, isolation_level='DEFERRED')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS department (
                dept_id INTEGER PRIMARY KEY AUTOINCREMENT,
                dept_name TEXT UNIQUE NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employee (
                emp_id INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_name TEXT NOT NULL,
                dept_id INTEGER NOT NULL,
                FOREIGN KEY (dept_id) REFERENCES department(dept_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS salary (
                sal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_id INTEGER NOT NULL,
                basic_pay REAL NOT NULL,
                allowance REAL NOT NULL,
                deduction REAL NOT NULL,
                FOREIGN KEY (emp_id) REFERENCES employee(emp_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS work_record (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_id INTEGER NOT NULL,
                work_hours REAL NOT NULL,
                FOREIGN KEY (emp_id) REFERENCES employee(emp_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill (
                skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT UNIQUE NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employee_skill (
                emp_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                PRIMARY KEY (emp_id, skill_id),
                FOREIGN KEY (emp_id) REFERENCES employee(emp_id),
                FOREIGN KEY (skill_id) REFERENCES skill(skill_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS certification (
                cert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cert_name TEXT UNIQUE NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employee_certification (
                emp_id INTEGER NOT NULL,
                cert_id INTEGER NOT NULL,
                PRIMARY KEY (emp_id, cert_id),
                FOREIGN KEY (emp_id) REFERENCES employee(emp_id),
                FOREIGN KEY (cert_id) REFERENCES certification(cert_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT UNIQUE NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultant (
                consultant_id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultant_name TEXT UNIQUE NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultant_skill (
                consultant_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                PRIMARY KEY (consultant_id, skill_id),
                FOREIGN KEY (consultant_id) REFERENCES consultant(consultant_id),
                FOREIGN KEY (skill_id) REFERENCES skill(skill_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_project (
                skill_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                PRIMARY KEY (skill_id, project_id),
                FOREIGN KEY (skill_id) REFERENCES skill(skill_id),
                FOREIGN KEY (project_id) REFERENCES project(project_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultant_project (
                consultant_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                PRIMARY KEY (consultant_id, project_id),
                FOREIGN KEY (consultant_id) REFERENCES consultant(consultant_id),
                FOREIGN KEY (project_id) REFERENCES project(project_id)
            )
        ''')
        
        conn.commit()
        print("✅ Main database initialized with 1NF-5NF tables!")
    
    init_distributed_nodes()

def init_distributed_nodes():
    with get_db_connection(NODE1_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS department (
                dept_id INTEGER PRIMARY KEY,
                dept_name TEXT UNIQUE NOT NULL
            )
        ''')
        conn.commit()
        print("✅ Node 1 (Department) initialized")
    
    with get_db_connection(NODE2_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employee (
                emp_id INTEGER PRIMARY KEY,
                emp_name TEXT NOT NULL,
                dept_id INTEGER NOT NULL
            )
        ''')
        conn.commit()
        print("✅ Node 2 (Employee) initialized")
    
    with get_db_connection(NODE3_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS salary (
                sal_id INTEGER PRIMARY KEY,
                emp_id INTEGER NOT NULL,
                basic_pay REAL NOT NULL,
                allowance REAL NOT NULL,
                deduction REAL NOT NULL
            )
        ''')
        conn.commit()
        print("✅ Node 3 (Salary) initialized")
    
    with get_db_connection(NODE4_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS work_record (
                record_id INTEGER PRIMARY KEY,
                emp_id INTEGER NOT NULL,
                work_hours REAL NOT NULL
            )
        ''')
        conn.commit()
        print("✅ Node 4 (Work Record) initialized")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_payroll():
    emp_name = request.form.get('emp_name', '')
    dept_name = request.form.get('dept_name', '')
    basic_pay = float(request.form.get('basic_pay', 0))
    allowance = float(request.form.get('allowance', 0))
    deduction = float(request.form.get('deduction', 0))
    work_hours = float(request.form.get('work_hours', 0))
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT dept_id FROM department WHERE dept_name = ?', (dept_name,))
            dept = cursor.fetchone()
            
            if dept is None:
                cursor.execute('INSERT INTO department (dept_name) VALUES (?)', (dept_name,))
                dept_id = cursor.lastrowid
            else:
                dept_id = dept['dept_id']
            
            cursor.execute('INSERT INTO employee (emp_name, dept_id) VALUES (?, ?)', 
                         (emp_name, dept_id))
            emp_id = cursor.lastrowid
            
            cursor.execute('INSERT INTO salary (emp_id, basic_pay, allowance, deduction) VALUES (?, ?, ?, ?)',
                         (emp_id, basic_pay, allowance, deduction))
            
            cursor.execute('INSERT INTO work_record (emp_id, work_hours) VALUES (?, ?)',
                         (emp_id, work_hours))
            
            conn.commit()
        
        sync_to_distributed_nodes()
        
        return redirect(url_for('report'))
    except Exception as e:
        return f"Error: {str(e)}", 500

def sync_to_distributed_nodes():
    with get_db_connection() as main_conn:
        main_cursor = main_conn.cursor()
        
        main_cursor.execute('SELECT dept_id, dept_name FROM department')
        departments = main_cursor.fetchall()
        with get_db_connection(NODE1_DB) as node_conn:
            node_cursor = node_conn.cursor()
            for dept in departments:
                node_cursor.execute('INSERT OR REPLACE INTO department VALUES (?, ?)', 
                                  (dept['dept_id'], dept['dept_name']))
            node_conn.commit()
        
        main_cursor.execute('SELECT emp_id, emp_name, dept_id FROM employee')
        employees = main_cursor.fetchall()
        with get_db_connection(NODE2_DB) as node_conn:
            node_cursor = node_conn.cursor()
            for emp in employees:
                node_cursor.execute('INSERT OR REPLACE INTO employee VALUES (?, ?, ?)', 
                                  (emp['emp_id'], emp['emp_name'], emp['dept_id']))
            node_conn.commit()
        
        main_cursor.execute('SELECT sal_id, emp_id, basic_pay, allowance, deduction FROM salary')
        salaries = main_cursor.fetchall()
        with get_db_connection(NODE3_DB) as node_conn:
            node_cursor = node_conn.cursor()
            for sal in salaries:
                node_cursor.execute('INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?)', 
                                  (sal['sal_id'], sal['emp_id'], sal['basic_pay'], 
                                   sal['allowance'], sal['deduction']))
            node_conn.commit()
        
        main_cursor.execute('SELECT record_id, emp_id, work_hours FROM work_record')
        records = main_cursor.fetchall()
        with get_db_connection(NODE4_DB) as node_conn:
            node_cursor = node_conn.cursor()
            for rec in records:
                node_cursor.execute('INSERT OR REPLACE INTO work_record VALUES (?, ?, ?)', 
                                  (rec['record_id'], rec['emp_id'], rec['work_hours']))
            node_conn.commit()

@app.route('/normalized')
def normalized():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM department')
        departments = cursor.fetchall()
        
        cursor.execute('SELECT * FROM employee')
        employees = cursor.fetchall()
        
        cursor.execute('SELECT * FROM salary')
        salaries = cursor.fetchall()
        
        cursor.execute('SELECT * FROM work_record')
        work_records = cursor.fetchall()
        
        cursor.execute('''
            SELECT e.emp_id, e.emp_name, s.skill_name
            FROM employee e
            LEFT JOIN employee_skill es ON e.emp_id = es.emp_id
            LEFT JOIN skill s ON es.skill_id = s.skill_id
        ''')
        employee_skills = cursor.fetchall()
        
        cursor.execute('''
            SELECT e.emp_id, e.emp_name, c.cert_name
            FROM employee e
            LEFT JOIN employee_certification ec ON e.emp_id = ec.emp_id
            LEFT JOIN certification c ON ec.cert_id = c.cert_id
        ''')
        employee_certs = cursor.fetchall()
        
        cursor.execute('SELECT * FROM consultant')
        consultants = cursor.fetchall()
        
        cursor.execute('''
            SELECT c.consultant_name, s.skill_name
            FROM consultant c
            JOIN consultant_skill cs ON c.consultant_id = cs.consultant_id
            JOIN skill s ON cs.skill_id = s.skill_id
        ''')
        consultant_skills = cursor.fetchall()
        
        cursor.execute('''
            SELECT s.skill_name, p.project_name
            FROM skill s
            JOIN skill_project sp ON s.skill_id = sp.skill_id
            JOIN project p ON sp.project_id = p.project_id
        ''')
        skill_projects = cursor.fetchall()
        
        cursor.execute('''
            SELECT c.consultant_name, p.project_name
            FROM consultant c
            JOIN consultant_project cp ON c.consultant_id = cp.consultant_id
            JOIN project p ON cp.project_id = p.project_id
        ''')
        consultant_projects = cursor.fetchall()
    
    return render_template('normalized.html',
                         departments=departments,
                         employees=employees,
                         salaries=salaries,
                         work_records=work_records,
                         employee_skills=employee_skills,
                         employee_certs=employee_certs,
                         consultants=consultants,
                         consultant_skills=consultant_skills,
                         skill_projects=skill_projects,
                         consultant_projects=consultant_projects)

@app.route('/database-tables')
def database_tables():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM department')
        departments = cursor.fetchall()
        
        cursor.execute('SELECT e.*, d.dept_name FROM employee e LEFT JOIN department d ON e.dept_id = d.dept_id')
        employees = cursor.fetchall()
        
        cursor.execute('SELECT s.*, e.emp_name FROM salary s LEFT JOIN employee e ON s.emp_id = e.emp_id')
        salaries = cursor.fetchall()
        
        cursor.execute('SELECT w.*, e.emp_name FROM work_record w LEFT JOIN employee e ON w.emp_id = e.emp_id')
        work_records = cursor.fetchall()
    
    return render_template('database_tables.html',
                         departments=departments,
                         employees=employees,
                         salaries=salaries,
                         work_records=work_records)

@app.route('/report')
def report():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                e.emp_id,
                e.emp_name,
                d.dept_name,
                s.basic_pay,
                s.allowance,
                s.deduction,
                (s.basic_pay + s.allowance - s.deduction) as net_pay,
                w.work_hours
            FROM employee e
            INNER JOIN department d ON e.dept_id = d.dept_id
            INNER JOIN salary s ON e.emp_id = s.emp_id
            INNER JOIN work_record w ON e.emp_id = w.emp_id
            ORDER BY e.emp_id DESC
        '''
        
        cursor.execute(query)
        payroll_data = cursor.fetchall()
    
    return render_template('report.html', payroll_data=payroll_data)

@app.route('/simulate-concurrency')
def simulate_concurrency():
    global concurrency_log
    concurrency_log = []
    
    def concurrent_read_operation(thread_id):
        try:
            start_time = time.time()
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) as cnt FROM employee')
                count = cursor.fetchone()['cnt']
                time.sleep(0.1)
            
            end_time = time.time()
            log_entry = {
                'thread_id': thread_id,
                'operation': 'READ',
                'table': 'employee',
                'duration': round(end_time - start_time, 3),
                'status': 'Success - No lock required',
                'result': f'Read {count} records'
            }
            concurrency_log.append(log_entry)
            
        except Exception as e:
            concurrency_log.append({
                'thread_id': thread_id,
                'operation': 'READ',
                'status': f'Failed: {str(e)}'
            })
    
    def concurrent_write_conflict(thread_id, emp_id):
        try:
            start_time = time.time()
            with get_db_connection() as conn:
                cursor = conn.cursor()
                conn.execute('BEGIN IMMEDIATE')
                
                cursor.execute('SELECT basic_pay FROM salary WHERE emp_id = ?', (emp_id,))
                current_salary = cursor.fetchone()
                
                if current_salary:
                    new_salary = current_salary['basic_pay'] + (thread_id * 1000)
                    time.sleep(random.uniform(0.05, 0.15))
                    
                    cursor.execute('UPDATE salary SET basic_pay = ? WHERE emp_id = ?', 
                                 (new_salary, emp_id))
                    conn.commit()
                    
                    end_time = time.time()
                    log_entry = {
                        'thread_id': thread_id,
                        'operation': 'WRITE (Concurrent Update)',
                        'table': 'salary',
                        'emp_id': emp_id,
                        'duration': round(end_time - start_time, 3),
                        'status': 'Success - Transaction committed',
                        'result': f'Updated salary to {new_salary}'
                    }
                    concurrency_log.append(log_entry)
                else:
                    concurrency_log.append({
                        'thread_id': thread_id,
                        'operation': 'WRITE',
                        'status': 'Skipped - No employee found'
                    })
                    
        except sqlite3.OperationalError as e:
            concurrency_log.append({
                'thread_id': thread_id,
                'operation': 'WRITE (Concurrent Update)',
                'status': f'Blocked/Retried: {str(e)}',
                'note': 'Database locked by another transaction'
            })
        except Exception as e:
            concurrency_log.append({
                'thread_id': thread_id,
                'operation': 'WRITE',
                'status': f'Failed: {str(e)}'
            })
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT emp_id FROM employee LIMIT 1')
        test_emp = cursor.fetchone()
        test_emp_id = test_emp['emp_id'] if test_emp else None
    
    threads = []
    
    for i in range(1, 6):
        read_thread = threading.Thread(target=concurrent_read_operation, args=(i,))
        threads.append(read_thread)
    
    if test_emp_id:
        for i in range(10, 15):
            write_thread = threading.Thread(target=concurrent_write_conflict, args=(i, test_emp_id))
            threads.append(write_thread)
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    sorted_log = sorted(concurrency_log, key=lambda x: x.get('thread_id', 0))
    
    return render_template('concurrency_results.html',
                         results=sorted_log,
                         total_operations=len(threads),
                         test_emp_id=test_emp_id)

@app.route('/distributed-demo')
def distributed_demo():
    sync_to_distributed_nodes()
    
    with get_db_connection(NODE1_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT dept_id, dept_name FROM department')
        node1_data = [dict(row) for row in cursor.fetchall()]
    
    with get_db_connection(NODE2_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT emp_id, emp_name, dept_id FROM employee')
        node2_data = [dict(row) for row in cursor.fetchall()]
    
    with get_db_connection(NODE3_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT sal_id, emp_id, basic_pay, allowance, deduction FROM salary')
        node3_data = [dict(row) for row in cursor.fetchall()]
    
    with get_db_connection(NODE4_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT record_id, emp_id, work_hours FROM work_record')
        node4_data = [dict(row) for row in cursor.fetchall()]
    
    joined_data = []
    for emp in node2_data:
        emp_id = emp['emp_id']
        dept_name = next((d['dept_name'] for d in node1_data if d['dept_id'] == emp['dept_id']), 'Unknown')
        salary_info = next((s for s in node3_data if s['emp_id'] == emp_id), None)
        work_info = next((w for w in node4_data if w['emp_id'] == emp_id), None)
        
        if salary_info and work_info:
            joined_data.append({
                'emp_id': emp_id,
                'emp_name': emp['emp_name'],
                'dept_name': dept_name,
                'basic_pay': salary_info['basic_pay'],
                'allowance': salary_info['allowance'],
                'deduction': salary_info['deduction'],
                'work_hours': work_info['work_hours']
            })
    
    return jsonify({
        'message': 'Distributed Data Demonstration - Cross-Node Query',
        'architecture': {
            'Node_1': f'Department data (Database: {NODE1_DB})',
            'Node_2': f'Employee data (Database: {NODE2_DB})',
            'Node_3': f'Salary data (Database: {NODE3_DB})',
            'Node_4': f'Work record data (Database: {NODE4_DB})'
        },
        'raw_node_data': {
            'Node_1_Department': node1_data,
            'Node_2_Employee': node2_data,
            'Node_3_Salary': node3_data,
            'Node_4_WorkRecord': node4_data
        },
        'cross_node_join_result': joined_data,
        'explanation': 'Data is stored in separate database files (simulating distributed nodes). The cross-node join is performed programmatically by fetching data from each node and combining it.'
    })

@app.route('/4nf-5nf-demo')
def demo_4nf_5nf():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT emp_id FROM employee LIMIT 1')
        test_emp = cursor.fetchone()
        
        if test_emp:
            emp_id = test_emp['emp_id']
            
            cursor.execute('SELECT COUNT(*) as cnt FROM skill')
            if cursor.fetchone()['cnt'] == 0:
                skills = ['Python', 'JavaScript', 'SQL', 'Docker']
                for skill in skills:
                    cursor.execute('INSERT OR IGNORE INTO skill (skill_name) VALUES (?)', (skill,))
                
                for i in range(1, min(3, len(skills))):
                    cursor.execute('INSERT OR IGNORE INTO employee_skill (emp_id, skill_id) VALUES (?, ?)', 
                                 (emp_id, i))
            
            cursor.execute('SELECT COUNT(*) as cnt FROM certification')
            if cursor.fetchone()['cnt'] == 0:
                certs = ['AWS Certified', 'PMP', 'Scrum Master']
                for cert in certs:
                    cursor.execute('INSERT OR IGNORE INTO certification (cert_name) VALUES (?)', (cert,))
                
                for i in range(1, min(3, len(certs))):
                    cursor.execute('INSERT OR IGNORE INTO employee_certification (emp_id, cert_id) VALUES (?, ?)', 
                                 (emp_id, i))
            
            conn.commit()
        
        cursor.execute('''
            SELECT e.emp_name, s.skill_name
            FROM employee e
            JOIN employee_skill es ON e.emp_id = es.emp_id
            JOIN skill s ON es.skill_id = s.skill_id
        ''')
        skills_data = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT e.emp_name, c.cert_name
            FROM employee e
            JOIN employee_certification ec ON e.emp_id = ec.emp_id
            JOIN certification c ON ec.cert_id = c.cert_id
        ''')
        certs_data = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('SELECT COUNT(*) as cnt FROM consultant')
        if cursor.fetchone()['cnt'] == 0:
            consultants = ['Alice Smith', 'Bob Johnson']
            for name in consultants:
                cursor.execute('INSERT OR IGNORE INTO consultant (consultant_name) VALUES (?)', (name,))
            
            projects = ['Website Redesign', 'Mobile App']
            for name in projects:
                cursor.execute('INSERT OR IGNORE INTO project (project_name) VALUES (?)', (name,))
            
            cursor.execute('SELECT skill_id FROM skill WHERE skill_name = ?', ('Python',))
            python_skill = cursor.fetchone()
            cursor.execute('SELECT skill_id FROM skill WHERE skill_name = ?', ('JavaScript',))
            js_skill = cursor.fetchone()
            
            if python_skill and js_skill:
                cursor.execute('INSERT OR IGNORE INTO consultant_skill VALUES (1, ?)', (python_skill['skill_id'],))
                cursor.execute('INSERT OR IGNORE INTO consultant_skill VALUES (1, ?)', (js_skill['skill_id'],))
                cursor.execute('INSERT OR IGNORE INTO consultant_skill VALUES (2, ?)', (python_skill['skill_id'],))
                
                cursor.execute('INSERT OR IGNORE INTO skill_project VALUES (?, 1)', (python_skill['skill_id'],))
                cursor.execute('INSERT OR IGNORE INTO skill_project VALUES (?, 2)', (js_skill['skill_id'],))
                cursor.execute('INSERT OR IGNORE INTO skill_project VALUES (?, 2)', (python_skill['skill_id'],))
                
                cursor.execute('INSERT OR IGNORE INTO consultant_project VALUES (1, 1)')
                cursor.execute('INSERT OR IGNORE INTO consultant_project VALUES (1, 2)')
                cursor.execute('INSERT OR IGNORE INTO consultant_project VALUES (2, 2)')
            
            conn.commit()
        
        cursor.execute('''
            SELECT c.consultant_name, s.skill_name
            FROM consultant c
            JOIN consultant_skill cs ON c.consultant_id = cs.consultant_id
            JOIN skill s ON cs.skill_id = s.skill_id
        ''')
        consultant_skills = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT s.skill_name, p.project_name
            FROM skill s
            JOIN skill_project sp ON s.skill_id = sp.skill_id
            JOIN project p ON sp.project_id = p.project_id
        ''')
        skill_projects = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT c.consultant_name, p.project_name
            FROM consultant c
            JOIN consultant_project cp ON c.consultant_id = cp.consultant_id
            JOIN project p ON cp.project_id = p.project_id
        ''')
        consultant_projects = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT DISTINCT c.consultant_name, s.skill_name, p.project_name
            FROM consultant c
            JOIN consultant_skill cs ON c.consultant_id = cs.consultant_id
            JOIN skill s ON cs.skill_id = s.skill_id
            JOIN skill_project sp ON s.skill_id = sp.skill_id
            JOIN project p ON sp.project_id = p.project_id
            JOIN consultant_project cp ON c.consultant_id = cp.consultant_id AND p.project_id = cp.project_id
        ''')
        reconstructed = [dict(row) for row in cursor.fetchall()]
    
    return jsonify({
        'message': '4NF and 5NF Demonstration with Complete Examples',
        '4NF_explanation': 'Multi-valued dependencies are separated. Employee skills and certifications are independent.',
        '4NF_example': {
            'employee_skills': skills_data,
            'employee_certifications': certs_data,
            'explanation': 'An employee can have multiple skills AND multiple certifications independently. Storing them together would create redundancy.',
            'benefit': 'No redundant data - if an employee has 3 skills and 2 certs, we need only 5 rows total, not 6.'
        },
        '5NF_explanation': 'Join dependencies are eliminated by decomposing into binary projections that can be losslessly joined.',
        '5NF_example': {
            'scenario': 'Consultant-Skill-Project relationship',
            'business_rule': 'A consultant can work on a project only if they have a skill required by that project',
            'decomposed_tables': {
                'consultant_skill': consultant_skills,
                'skill_project': skill_projects,
                'consultant_project': consultant_projects
            },
            'lossless_join_reconstruction': reconstructed,
            'explanation': 'The three binary tables (consultant↔skill, skill↔project, consultant↔project) are joined to reconstruct the full triple (consultant, skill, project) without information loss.',
            'benefit': 'Eliminates join dependencies - each binary relationship is stored once, and the full relationship is derived through joins.'
        }
    })

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
