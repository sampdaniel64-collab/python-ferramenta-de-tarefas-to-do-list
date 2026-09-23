"""
To-Do List - Atividades, Pendencias e Objetivos
Backend: Python + Flask + SQLite (CRUD completo)
Autor: projeto gerado para GitHub
"""

import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "todos.db")

app = Flask(__name__)

# ---------------- Banco de dados ----------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT DEFAULT '',
            tipo TEXT NOT NULL DEFAULT 'atividade'
                CHECK (tipo IN ('atividade', 'pendencia', 'objetivo')),
            prioridade TEXT NOT NULL DEFAULT 'media'
                CHECK (prioridade IN ('baixa', 'media', 'alta')),
            concluida INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL
        )
    """)
    db.commit()
    db.close()

# ---------------- Helpers ----------------

def contar_estatisticas(db):
    total = db.execute("SELECT COUNT(*) FROM tarefas").fetchone()[0]
    concluidas = db.execute("SELECT COUNT(*) FROM tarefas WHERE concluida = 1").fetchone()[0]
    pendentes = total - concluidas
    return {"total": total, "concluidas": concluidas, "pendentes": pendentes}

# ---------------- Rotas - Frontend (CRUD) ----------------

@app.route("/", methods=["GET"])
def index():
    """READ - Lista tarefas com filtros e busca."""
    filtro = request.args.get("filtro", "todas")   # todas | pendentes | concluidas
    tipo = request.args.get("tipo", "todos")       # todos | atividade | pendencia | objetivo
    busca = request.args.get("busca", "").strip()

    db = get_db()
    query = "SELECT * FROM tarefas WHERE 1=1"
    params = []

    if filtro == "pendentes":
        query += " AND concluida = 0"
    elif filtro == "concluidas":
        query += " AND concluida = 1"

    if tipo in ("atividade", "pendencia", "objetivo"):
        query += " AND tipo = ?"
        params.append(tipo)

    if busca:
        query += " AND (titulo LIKE ? OR descricao LIKE ?)"
        params.extend([f"%{busca}%", f"%{busca}%"])

    query += " ORDER BY concluida ASC, criado_em DESC"
    tarefas = db.execute(query, params).fetchall()
    stats = contar_estatisticas(db)

    return render_template(
        "index.html",
        tarefas=tarefas,
        stats=stats,
        filtro=filtro,
        tipo=tipo,
        busca=busca,
    )

@app.route("/adicionar", methods=["POST"])
def adicionar():
    """CREATE - Cria nova tarefa."""
    titulo = request.form.get("titulo", "").strip()
    descricao = request.form.get("descricao", "").strip()
    tipo = request.form.get("tipo", "atividade")
    prioridade = request.form.get("prioridade", "media")

    if tipo not in ("atividade", "pendencia", "objetivo"):
        tipo = "atividade"
    if prioridade not in ("baixa", "media", "alta"):
        prioridade = "media"
    if not titulo:
        return redirect(url_for("index"))

    db = get_db()
    db.execute(
        "INSERT INTO tarefas (titulo, descricao, tipo, prioridade, concluida, criado_em)"
        " VALUES (?, ?, ?, ?, 0, ?)",
        (titulo, descricao, tipo, prioridade, datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()
    return redirect(url_for("index"))

@app.route("/concluir/<int:tarefa_id>", methods=["POST"])
def concluir(tarefa_id):
    """UPDATE - Alterna concluida / pendente."""
    db = get_db()
    atual = db.execute("SELECT concluida FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()
    if atual is None:
        return redirect(url_for("index"))
    novo = 0 if atual["concluida"] else 1
    db.execute("UPDATE tarefas SET concluida = ? WHERE id = ?", (novo, tarefa_id))
    db.commit()
    return redirect(url_for("index"))

@app.route("/editar/<int:tarefa_id>", methods=["GET", "POST"])
def editar(tarefa_id):
    """UPDATE - Edita titulo, descricao, tipo e prioridade."""
    db = get_db()
    tarefa = db.execute("SELECT * FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()
    if tarefa is None:
        return redirect(url_for("index"))

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        tipo = request.form.get("tipo", "atividade")
        prioridade = request.form.get("prioridade", "media")
        if tipo not in ("atividade", "pendencia", "objetivo"):
            tipo = "atividade"
        if prioridade not in ("baixa", "media", "alta"):
            prioridade = "media"
        if titulo:
            db.execute(
                "UPDATE tarefas SET titulo = ?, descricao = ?, tipo = ?, prioridade = ? WHERE id = ?",
                (titulo, descricao, tipo, prioridade, tarefa_id),
            )
            db.commit()
        return redirect(url_for("index"))

    return render_template("edit.html", tarefa=tarefa)

@app.route("/excluir/<int:tarefa_id>", methods=["POST"])
def excluir(tarefa_id):
    """DELETE - Remove tarefa."""
    db = get_db()
    db.execute("DELETE FROM tarefas WHERE id = ?", (tarefa_id,))
    db.commit()
    return redirect(url_for("index"))

# ---------------- API JSON (CRUD REST) ----------------

@app.route("/api/tarefas", methods=["GET"])
def api_listar():
    db = get_db()
    rows = db.execute("SELECT * FROM tarefas ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/tarefas", methods=["POST"])
def api_criar():
    dados = request.get_json(force=True)
    titulo = (dados.get("titulo") or "").strip()
    if not titulo:
        return jsonify({"erro": "titulo e obrigatorio"}), 400
    tipo = dados.get("tipo", "atividade")
    prioridade = dados.get("prioridade", "media")
    if tipo not in ("atividade", "pendencia", "objetivo"):
        tipo = "atividade"
    if prioridade not in ("baixa", "media", "alta"):
        prioridade = "media"
    db = get_db()
    cur = db.execute(
        "INSERT INTO tarefas (titulo, descricao, tipo, prioridade, concluida, criado_em)"
        " VALUES (?, ?, ?, ?, 0, ?)",
        (titulo, dados.get("descricao", ""), tipo, prioridade,
         datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()
    nova = db.execute("SELECT * FROM tarefas WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(nova)), 201

@app.route("/api/tarefas/<int:tarefa_id>", methods=["PUT"])
def api_atualizar(tarefa_id):
    dados = request.get_json(force=True)
    db = get_db()
    tarefa = db.execute("SELECT * FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()
    if tarefa is None:
        return jsonify({"erro": "nao encontrada"}), 404
    db.execute(
        """UPDATE tarefas SET
               titulo = ?, descricao = ?, tipo = ?,
               prioridade = ?, concluida = ?
           WHERE id = ?""",
        (
            dados.get("titulo", tarefa["titulo"]),
            dados.get("descricao", tarefa["descricao"]),
            dados.get("tipo", tarefa["tipo"]),
            dados.get("prioridade", tarefa["prioridade"]),
            int(bool(dados.get("concluida", tarefa["concluida"]))),
            tarefa_id,
        ),
    )
    db.commit()
    atual = db.execute("SELECT * FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()
    return jsonify(dict(atual))

@app.route("/api/tarefas/<int:tarefa_id>", methods=["DELETE"])
def api_excluir(tarefa_id):
    db = get_db()
    db.execute("DELETE FROM tarefas WHERE id = ?", (tarefa_id,))
    db.commit()
    return jsonify({"ok": True})

# ---------------- Main ----------------

init_db()  # garante tabela em import (gunicorn/deploy) e em clones frescos

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="127.0.0.1", port=port)
