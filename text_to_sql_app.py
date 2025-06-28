import streamlit as st
import pandas as pd
import sqlite3
import json
from typing import Dict, List, Optional
import time

# Configure page
st.set_page_config(
    page_title="Text-to-SQL Generator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mock database connections and schemas (replace with actual database connections)
MOCK_DATABASES = {
    "ecommerce_db": {
        "users": {
            "ddl": """CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);""",
            "columns": ["id", "username", "email", "created_at", "last_login", "is_active"]
        },
        "products": {
            "ddl": """CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category_id INTEGER,
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);""",
            "columns": ["id", "name", "description", "price", "category_id", "stock_quantity", "created_at"]
        },
        "orders": {
            "ddl": """CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);""",
            "columns": ["id", "user_id", "total_amount", "status", "order_date"]
        },
        "categories": {
            "ddl": """CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id INTEGER,
    FOREIGN KEY (parent_id) REFERENCES categories(id)
);""",
            "columns": ["id", "name", "description", "parent_id"]
        }
    },
    "hr_system": {
        "employees": {
            "ddl": """CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    department_id INTEGER,
    salary DECIMAL(10,2),
    hire_date DATE NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);""",
            "columns": ["id", "first_name", "last_name", "email", "department_id", "salary", "hire_date"]
        },
        "departments": {
            "ddl": """CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    budget DECIMAL(12,2),
    manager_id INTEGER,
    FOREIGN KEY (manager_id) REFERENCES employees(id)
);""",
            "columns": ["id", "name", "budget", "manager_id"]
        }
    }
}

def mock_llm_query(text_query: str, selected_tables: List[str], database: str) -> str:
    """Mock LLM function - replace with actual LLM API call"""
    time.sleep(1)  # Simulate API call delay
    
    # Simple keyword-based mock responses
    query_lower = text_query.lower()
    
    if "users" in query_lower and "count" in query_lower:
        return "SELECT COUNT(*) as total_users FROM users WHERE is_active = TRUE;"
    elif "products" in query_lower and "price" in query_lower:
        return "SELECT name, price FROM products WHERE price > 100 ORDER BY price DESC;"
    elif "orders" in query_lower and "total" in query_lower:
        return "SELECT SUM(total_amount) as total_revenue FROM orders WHERE status = 'completed';"
    elif "employees" in query_lower and "salary" in query_lower:
        return "SELECT first_name, last_name, salary FROM employees WHERE salary > 50000 ORDER BY salary DESC;"
    else:
        return f"SELECT * FROM {selected_tables[0] if selected_tables else 'table_name'} LIMIT 10;"

def mock_execute_query(sql_query: str, database: str) -> pd.DataFrame:
    """Mock query execution - replace with actual database execution"""
    time.sleep(0.5)  # Simulate query execution delay
    
    # Generate mock data based on query type
    query_lower = sql_query.lower()
    
    if "count(*)" in query_lower and "users" in query_lower:
        return pd.DataFrame({"total_users": [1247]})
    elif "name, price" in query_lower and "products" in query_lower:
        return pd.DataFrame({
            "name": ["Premium Laptop", "Gaming Monitor", "Wireless Headphones", "Smart Watch", "Tablet Pro"],
            "price": [1299.99, 849.99, 299.99, 399.99, 899.99]
        })
    elif "sum(total_amount)" in query_lower and "orders" in query_lower:
        return pd.DataFrame({"total_revenue": [2845672.50]})
    elif "first_name, last_name, salary" in query_lower and "employees" in query_lower:
        return pd.DataFrame({
            "first_name": ["Alice", "Bob", "Carol", "David", "Emma"],
            "last_name": ["Johnson", "Smith", "Brown", "Wilson", "Davis"],
            "salary": [85000.00, 92000.00, 78000.00, 105000.00, 88000.00]
        })
    elif "users" in query_lower:
        return pd.DataFrame({
            "id": range(1, 6),
            "username": ["alice_j", "bob_smith", "carol_b", "david_w", "emma_d"],
            "email": ["alice@email.com", "bob@email.com", "carol@email.com", "david@email.com", "emma@email.com"],
            "created_at": ["2024-01-15", "2024-02-20", "2024-03-10", "2024-04-05", "2024-05-12"],
            "is_active": [True, True, False, True, True]
        })
    else:
        # Default sample data
        return pd.DataFrame({
            "id": range(1, 6),
            "sample_column": ["Data 1", "Data 2", "Data 3", "Data 4", "Data 5"],
            "value": [100, 200, 300, 400, 500]
        })

def main():
    # App header
    st.title("🔍 Text-to-SQL Generator")
    st.markdown("Convert natural language queries into SQL statements")
    
    # Initialize session state
    if 'generated_sql' not in st.session_state:
        st.session_state.generated_sql = ""
    if 'query_results' not in st.session_state:
        st.session_state.query_results = None
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []

    # Sidebar for database selection
    with st.sidebar:
        st.header("🗄️ Database Configuration")
        
        # Database selection
        selected_db = st.selectbox(
            "Select Database",
            options=list(MOCK_DATABASES.keys()),
            format_func=lambda x: x.replace("_", " ").title(),
            help="Choose the database you want to query"
        )
        
        # Schema info (for this demo, we'll show table count)
        if selected_db:
            st.info(f"📊 Schema: {len(MOCK_DATABASES[selected_db])} tables available")
        
        # Table selection
        st.subheader("📋 Table Selection")
        available_tables = list(MOCK_DATABASES[selected_db].keys()) if selected_db else []
        
        selected_tables = st.multiselect(
            "Select Tables",
            options=available_tables,
            default=available_tables[:2] if available_tables else [],
            help="Select one or more tables for your query context"
        )
        
        # Connection status
        st.success("✅ Connected" if selected_db else "❌ No database selected")

    # Table DDL Section - Moved to top
    if selected_tables:
        st.header("🏗️ Table Structures (DDL)")
        
        tabs = st.tabs([table.replace("_", " ").title() for table in selected_tables])
        
        for i, table in enumerate(selected_tables):
            with tabs[i]:
                col_ddl1, col_ddl2 = st.columns([2, 1])
                
                with col_ddl1:
                    st.subheader(f"📋 {table.replace('_', ' ').title()} DDL")
                    st.code(MOCK_DATABASES[selected_db][table]["ddl"], language="sql")
                
                with col_ddl2:
                    st.subheader("🔗 Columns")
                    columns_df = pd.DataFrame({
                        "Column": MOCK_DATABASES[selected_db][table]["columns"],
                        "Index": range(1, len(MOCK_DATABASES[selected_db][table]["columns"]) + 1)
                    })
                    st.dataframe(columns_df, hide_index=True, use_container_width=True)
        
        st.markdown("---")  # Separator between sections

    # Main content area - Query Input, Generated SQL and Data Results
    st.header("🔍 Query Workspace")
    
    # Top row: Query Input and Generated SQL
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Query Input")
        
        # Text query input
        text_query = st.text_area(
            "Enter your question in natural language:",
            placeholder="e.g., 'Show me all users who registered last month' or 'What are the top 5 products by sales?'",
            height=100,
            help="Describe what you want to know from your database in plain English"
        )
        
        # Generate button
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            generate_btn = st.button(
                "🚀 Generate SQL",
                type="primary",
                disabled=not (text_query and selected_tables and selected_db),
                use_container_width=True
            )
        
        with col_btn2:
            clear_btn = st.button(
                "🗑️ Clear All",
                use_container_width=True
            )
        
        # Generate SQL query
        if generate_btn:
            with st.spinner("Generating SQL query..."):
                try:
                    generated_sql = mock_llm_query(text_query, selected_tables, selected_db)
                    st.session_state.generated_sql = generated_sql
                    st.session_state.query_results = None  # Reset results when new SQL is generated
                    
                    # Add to history
                    st.session_state.query_history.append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "question": text_query,
                        "sql": generated_sql,
                        "tables": selected_tables.copy()
                    })
                    
                    st.success("✅ SQL query generated successfully!")
                except Exception as e:
                    st.error(f"❌ Error generating SQL: {str(e)}")
        
        if clear_btn:
            st.session_state.generated_sql = ""
            st.session_state.query_results = None
            st.rerun()
    
    with col2:
        st.subheader("⚡ Generated SQL")
        
        if st.session_state.generated_sql:
            st.code(st.session_state.generated_sql, language="sql")
            
            # Action buttons
            col_sql1, col_sql2, col_sql3 = st.columns([1, 1, 1])
            
            with col_sql1:
                if st.button("📋 Copy SQL", key="copy_sql", use_container_width=True):
                    st.success("SQL copied to clipboard!")
            
            with col_sql2:
                execute_btn = st.button("▶️ Execute", key="execute_sql", use_container_width=True, type="primary")
            
            with col_sql3:
                if st.button("💡 Explain", key="explain_sql", use_container_width=True):
                    with st.expander("Query Explanation", expanded=True):
                        st.markdown("""
                        **Query Breakdown:**
                        - **Tables Used:** """ + ", ".join(selected_tables) + """
                        - **Operation:** Data retrieval/aggregation
                        - **Purpose:** Answers the natural language question provided
                        """)
            
            # Execute SQL query
            if execute_btn:
                with st.spinner("Executing query on database..."):
                    try:
                        query_results = mock_execute_query(st.session_state.generated_sql, selected_db)
                        st.session_state.query_results = query_results
                        st.success(f"✅ Query executed successfully! Retrieved {len(query_results)} rows.")
                    except Exception as e:
                        st.error(f"❌ Error executing query: {str(e)}")
        else:
            st.info("👆 Enter a question and click 'Generate SQL' to see the result here")
    
    # Bottom section: Query Results
    if st.session_state.query_results is not None:
        st.markdown("---")
        st.header("📊 Query Results")
        
        # Results summary
        col_summary1, col_summary2, col_summary3 = st.columns([1, 1, 2])
        
        with col_summary1:
            st.metric("Rows Returned", len(st.session_state.query_results))
        
        with col_summary2:
            st.metric("Columns", len(st.session_state.query_results.columns))
        
        with col_summary3:
            # Download button placeholder
            st.markdown("**Export Options:**")
            col_exp1, col_exp2 = st.columns([1, 1])
            with col_exp1:
                if st.button("📥 Download CSV", key="download_csv"):
                    st.success("CSV download started!")
            with col_exp2:
                if st.button("📋 Copy Data", key="copy_data"):
                    st.success("Data copied to clipboard!")
        
        # Display the data
        st.dataframe(
            st.session_state.query_results,
            use_container_width=True,
            height=400
        )
        
        # Data insights (if applicable)
        if len(st.session_state.query_results) > 0:
            with st.expander("📈 Quick Data Insights", expanded=False):
                numeric_cols = st.session_state.query_results.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    st.write("**Numeric Columns Summary:**")
                    st.dataframe(st.session_state.query_results[numeric_cols].describe())
                else:
                    st.info("No numeric columns found for statistical summary.")

    # Query History Section
    if st.session_state.query_history:
        st.header("📚 Query History")
        
        with st.expander("View Previous Queries", expanded=False):
            for i, query in enumerate(reversed(st.session_state.query_history[-5:])):  # Show last 5
                st.markdown(f"**#{len(st.session_state.query_history)-i}** - {query['timestamp']}")
                st.markdown(f"**Question:** {query['question']}")
                st.code(query['sql'], language="sql")
                st.markdown(f"**Tables:** {', '.join(query['tables'])}")
                st.divider()

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 20px;'>
            <p>💡 <strong>Tip:</strong> Be specific in your questions for better SQL generation. 
            Include table names, column names, and conditions when possible.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()