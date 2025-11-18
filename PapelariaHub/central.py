from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "chave_super_secreta_papelaria" 
BANCO_DADOS = "estoque_central.db"


def conectar_banco():
    conexao = sqlite3.connect(BANCO_DADOS)
    conexao.row_factory = sqlite3.Row
    return conexao


def configurar_banco():
    """
    Cria as tabelas principais do sistema de papelaria, caso ainda não existam.
    """
    conexao = conectar_banco()

    # Tabela de grupos de itens (ex.: papel, escrita, organização, etc.)
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS grupos_itens (
            id_grupo INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_grupo TEXT NOT NULL UNIQUE,
            descricao_grupo TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Tabela de itens de papelaria em estoque
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS estoque_itens (
            id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_produto TEXT NOT NULL,
            grupo_id INTEGER,
            unidade TEXT,                  -- ex.: unidade, caixa, pacote
            limite_minimo INTEGER DEFAULT 5,
            quantidade INTEGER DEFAULT 0,
            posicao TEXT,                  -- ex.: prateleira A, gaveta 3
            anotacoes TEXT,
            status TEXT DEFAULT 'ativo',   -- ativo / inativo
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (grupo_id) REFERENCES grupos_itens (id_grupo)
        )
        """
    )

    # Tabela de transações de estoque (entradas e saídas)
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS transacoes_estoque (
            id_transacao INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            tipo_transacao TEXT NOT NULL,  -- entrada / saida
            valor INTEGER NOT NULL,        -- quantidade movimentada
            razao TEXT NOT NULL,           -- compra, venda, uso interno etc.
            observacoes TEXT,
            operador TEXT DEFAULT 'sistema',
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produto_id) REFERENCES estoque_itens (id_produto)
        )
        """
    )

    conexao.commit()
    conexao.close()


from flask import Flask, render_template
# já estava no seu código, mas garanta que tem "render_template"

@app.route("/")
def tela_principal():
    return render_template("painel.html")

@app.route("/grupos", methods=["GET", "POST"])
def gerenciar_grupos():
    """
    Tela para cadastrar e listar grupos de itens (papel, escrita, organização etc.).
    """
    conexao = conectar_banco()

    if request.method == "POST":
        nome = request.form.get("nome_grupo", "").strip()
        descricao = request.form.get("descricao_grupo", "").strip()

        if nome:
            try:
                conexao.execute(
                    "INSERT INTO grupos_itens (nome_grupo, descricao_grupo) VALUES (?, ?)",
                    (nome, descricao),
                )
                conexao.commit()
                flash("Grupo cadastrado com sucesso!", "sucesso")
            except sqlite3.IntegrityError:
                flash("Já existe um grupo com esse nome.", "erro")
        else:
            flash("O nome do grupo é obrigatório.", "erro")

        conexao.close()
        return redirect(url_for("gerenciar_grupos"))

    # Se for GET: buscar todos os grupos para exibir na tela
    grupos = conexao.execute(
        "SELECT id_grupo, nome_grupo, descricao_grupo, criado_em FROM grupos_itens ORDER BY nome_grupo"
    ).fetchall()
    conexao.close()

    return render_template("grupos.html", grupos=grupos)


if __name__ == "__main__":
    configurar_banco()
    app.run(debug=True)
