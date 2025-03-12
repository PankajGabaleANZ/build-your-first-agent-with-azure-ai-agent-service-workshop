import random

departments = {
    "Engineering": ["Software Engineer", "Data Engineer", "DevOps Engineer", "ML Engineer"],
    "Sales": ["Sales Associate", "Account Executive", "Sales Manager"],
    "Marketing": ["Marketing Coordinator", "SEO Specialist", "Brand Manager"],
    "HR": ["HR Coordinator", "Talent Acquisition", "HR Manager"],
    "Finance": ["Accountant", "Financial Analyst", "Finance Manager"],
    "Operations": ["Operations Coordinator", "Logistics Manager", "Supply Chain Analyst"]
}

salary_ranges = {
    "Software Engineer": [60000, 120000],
    "Data Engineer": [70000, 130000],
    "DevOps Engineer": [75000, 140000],
    "ML Engineer": [80000, 150000],
    "Sales Associate": [40000, 80000],
    "Account Executive": [50000, 90000],
    "Sales Manager": [60000, 110000],
    "Marketing Coordinator": [45000, 85000],
    "SEO Specialist": [50000, 95000],
    "Brand Manager": [60000, 105000],
    "HR Coordinator": [45000, 80000],
    "Talent Acquisition": [50000, 90000],
    "HR Manager": [65000, 110000],
    "Accountant": [55000, 95000],
    "Financial Analyst": [60000, 105000],
    "Finance Manager": [75000, 130000],
    "Operations Coordinator": [50000, 85000],
    "Logistics Manager": [60000, 110000],
    "Supply Chain Analyst": [55000, 100000]
}

regions = ["AFRICA", "ASIA-PACIFIC", "EUROPE", "MIDDLE EAST", "NORTH AMERICA", "LATIN AMERICA"]
years = list(range(2000, 2025))

def generate_employee_sql():
    insert_statements = []
    
    for i in range(500):  # Generate 500 employees
        department = random.choice(list(departments.keys()))
        position = random.choice(departments[department])
        salary_range = salary_ranges[position]
        salary = random.randint(salary_range[0], salary_range[1])
        age = random.randint(22, 60)
        year_joined = random.choice(years)
        region = random.choice(regions)
        name = f"Employee_{i}"  # Placeholder for random names

        insert_statements.append(
            f"INSERT INTO employees (name, age, department, position, salary, year_joined, region) "
            f"VALUES ('{name}', {age}, '{department}', '{position}', {salary}, {year_joined}, '{region}');"
        )

    return "\n".join(insert_statements)

sql_script = f"""
-- Create the employees table
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    age INTEGER,
    department TEXT,
    position TEXT,
    salary REAL,
    year_joined INTEGER,
    region TEXT
);

-- Insert random records into the table
{generate_employee_sql()}
"""

# Write to a SQL file
with open("populate_employees.sql", "w") as file:
    file.write(sql_script)

print("SQL script has been written to 'populate_employees.sql'")