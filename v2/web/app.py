from flask import Flask, render_template, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# config
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server', 'data', 'vlrgg_stats.db')

def execute_query(query):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        data = [dict(row) for row in rows]
        
        conn.close()
        
        return {
            "success": True,
            "data": data,
            "columns": columns,
            "count": len(data)
        }
        
    except Exception as e:
        return {"error": str(e)}

def get_tables_info():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        tables_info = []
        for table in tables:
            table_name = table[0]
            
            # récupérer les colonnes
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # cmopter les lignes
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Formater les colonnes
            formatted_columns = []
            for col in columns:
                formatted_columns.append({
                    'name': col[1],
                    'type': col[2],
                    'primary_key': bool(col[5])
                })
            
            tables_info.append({
                'name': table_name,
                'columns': formatted_columns,
                'row_count': row_count
            })
        
        conn.close()
        return tables_info
        
    except Exception as e:
        print(f"Erreur lors de la récupération des tables: {e}")
        return []

@app.route('/')
def index():
    # return render_template('index.html')
    return render_template('databaseQueryTool.html')

@app.route('/api/tables')
def api_tables():
    tables = get_tables_info()
    return jsonify(tables)

@app.route('/api/query', methods=['POST'])
def api_query():
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({"error": "Requête vide"})
    
    query_upper = query.upper().strip()
    if not (query_upper.startswith('SELECT') or query_upper.startswith('WITH')):
        return jsonify({"error": "Seules les requêtes SELECT et WITH sont autorisées. Pas touche aux données !"})
    
    result = execute_query(query)

    max_results = 2000
    if int(result.get("count", 0)) > max_results:
        result = {"error": f"Le nombre de résultats dépasse la limite de {max_results} lignes. Faut pas abuser non plus."}
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)