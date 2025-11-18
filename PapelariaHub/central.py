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

def calcular_previsao_estoque():
    """
    Para cada item, calcula a média diária de saída e a previsão
    de em quantos dias o estoque atual deve acabar.
    Retorna uma lista de dicionários com os dados.
    """
    conexao = conectar_banco()

    # Buscar todos os itens
    itens = conexao.execute(
        """
        SELECT id_produto, nome_produto, quantidade, limite_minimo
        FROM estoque_itens
        ORDER BY nome_produto
        """
    ).fetchall()

    previsoes = []

    for item in itens:
        produto_id = item["id_produto"]
        quantidade_atual = item["quantidade"] or 0

        # Buscar dados das saídas desse item
        dados_saida = conexao.execute(
            """
            SELECT
                SUM(valor) AS total_saida,
                MIN(data_registro) AS primeira_saida,
                MAX(data_registro) AS ultima_saida,
                (julianday(MAX(data_registro)) - julianday(MIN(data_registro)) + 1) AS dias_intervalo
            FROM transacoes_estoque
            WHERE tipo_transacao = 'saida' AND produto_id = ?
            """,
            (produto_id,),
        ).fetchone()

        total_saida = dados_saida["total_saida"]

        # Se nunca teve saída, não temos como prever
        if total_saida is None or total_saida == 0:
            previsoes.append(
                {
                    "nome_produto": item["nome_produto"],
                    "quantidade_atual": quantidade_atual,
                    "media_diaria": None,
                    "dias_restantes": None,
                    "status": "Sem consumo registrado",
                }
            )
            continue

        dias_intervalo = dados_saida["dias_intervalo"]

        # Evitar divisão por zero
        if dias_intervalo is None or dias_intervalo <= 0:
            previsoes.append(
                {
                    "nome_produto": item["nome_produto"],
                    "quantidade_atual": quantidade_atual,
                    "media_diaria": None,
                    "dias_restantes": None,
                    "status": "Período insuficiente",
                }
            )
            continue

        # Média de consumo por dia
        media_diaria = total_saida / dias_intervalo

        if media_diaria <= 0:
            previsoes.append(
                {
                    "nome_produto": item["nome_produto"],
                    "quantidade_atual": quantidade_atual,
                    "media_diaria": media_diaria,
                    "dias_restantes": None,
                    "status": "Consumo não significativo",
                }
            )
            continue

        # Dias até acabar (aproximação)
        dias_restantes = quantidade_atual / media_diaria if quantidade_atual > 0 else 0

        # Classificar status
        if dias_restantes == 0 and quantidade_atual == 0:
            status = "Esgotado"
        elif dias_restantes < 3:
            status = "Alerta crítico (pode acabar em poucos dias)"
        elif dias_restantes < 7:
            status = "Atenção (menos de uma semana)"
        else:
            status = "Estoque confortável"

        previsoes.append(
            {
                "nome_produto": item["nome_produto"],
                "quantidade_atual": quantidade_atual,
                "media_diaria": round(media_diaria, 2),
                "dias_restantes": round(dias_restantes, 1),
                "status": status,
            }
        )

    conexao.close()
    return previsoes

from flask import Flask, render_template

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

@app.route("/itens", methods=["GET", "POST"])
def gerenciar_itens():
    """
    Tela para cadastrar e listar itens de papelaria usando os grupos criados.
    """
    conexao = conectar_banco()

    # Buscar grupos para preencher o <select> do formulário
    grupos = conexao.execute(
        "SELECT id_grupo, nome_grupo FROM grupos_itens ORDER BY nome_grupo"
    ).fetchall()

    if request.method == "POST":
        nome_produto = request.form.get("nome_produto", "").strip()
        grupo_id = request.form.get("grupo_id")  # pode ser vazio
        unidade = request.form.get("unidade", "").strip()
        limite_minimo = request.form.get("limite_minimo", "0").strip()
        quantidade = request.form.get("quantidade", "0").strip()
        posicao = request.form.get("posicao", "").strip()
        anotacoes = request.form.get("anotacoes", "").strip()

        if not nome_produto:
            flash("O nome do produto é obrigatório.", "erro")
        else:
            try:
                conexao.execute(
                    """
                    INSERT INTO estoque_itens
                    (nome_produto, grupo_id, unidade, limite_minimo, quantidade, posicao, anotacoes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        nome_produto,
                        grupo_id if grupo_id else None,
                        unidade,
                        int(limite_minimo or 0),
                        int(quantidade or 0),
                        posicao,
                        anotacoes,
                    ),
                )
                conexao.commit()
                flash("Item cadastrado com sucesso!", "sucesso")
            except Exception as e:
                print("Erro ao inserir item:", e)
                flash("Erro ao cadastrar o item.", "erro")

        conexao.close()
        return redirect(url_for("gerenciar_itens"))

    # Se for GET: buscar todos os itens com o nome do grupo
    itens = conexao.execute(
        """
        SELECT
            e.id_produto,
            e.nome_produto,
            e.unidade,
            e.limite_minimo,
            e.quantidade,
            e.posicao,
            e.status,
            g.nome_grupo
        FROM estoque_itens e
        LEFT JOIN grupos_itens g ON g.id_grupo = e.grupo_id
        ORDER BY e.nome_produto
        """
    ).fetchall()

    conexao.close()
    return render_template("itens.html", itens=itens, grupos=grupos)

@app.route("/movimentacoes", methods=["GET", "POST"])
def movimentar_estoque():
    """
    Tela para registrar entradas e saídas de itens de papelaria.
    Atualiza a quantidade em estoque e guarda o histórico na tabela
    transacoes_estoque.
    """
    conexao = conectar_banco()

    # Itens para preencher o select no formulário
    itens = conexao.execute(
        "SELECT id_produto, nome_produto, quantidade FROM estoque_itens ORDER BY nome_produto"
    ).fetchall()

    if request.method == "POST":
        produto_id = request.form.get("produto_id")
        tipo = request.form.get("tipo_transacao")  # entrada / saida
        valor = request.form.get("valor", "0").strip()
        razao = request.form.get("razao", "").strip()
        observacoes = request.form.get("observacoes", "").strip()
        operador = request.form.get("operador", "").strip() or "usuario"

        # Validações básicas
        if not produto_id or not tipo or not valor or not razao:
            flash("Preencha todos os campos obrigatórios.", "erro")
            conexao.close()
            return redirect(url_for("movimentar_estoque"))

        try:
            valor_int = int(valor)
        except ValueError:
            flash("A quantidade deve ser um número inteiro.", "erro")
            conexao.close()
            return redirect(url_for("movimentar_estoque"))

        if valor_int <= 0:
            flash("A quantidade deve ser maior que zero.", "erro")
            conexao.close()
            return redirect(url_for("movimentar_estoque"))

        # Buscar quantidade atual do item
        item = conexao.execute(
            "SELECT quantidade FROM estoque_itens WHERE id_produto = ?",
            (produto_id,),
        ).fetchone()

        if not item:
            flash("Item não encontrado.", "erro")
            conexao.close()
            return redirect(url_for("movimentar_estoque"))

        quantidade_atual = item["quantidade"] or 0

        # Calcular nova quantidade
        if tipo == "entrada":
            nova_qtd = quantidade_atual + valor_int
        elif tipo == "saida":
            if valor_int > quantidade_atual:
                flash("Não é possível registrar saída maior que o estoque disponível.", "erro")
                conexao.close()
                return redirect(url_for("movimentar_estoque"))
            nova_qtd = quantidade_atual - valor_int
        else:
            flash("Tipo de transação inválido.", "erro")
            conexao.close()
            return redirect(url_for("movimentar_estoque"))

        # Registrar na tabela de transações
        conexao.execute(
            """
            INSERT INTO transacoes_estoque
            (produto_id, tipo_transacao, valor, razao, observacoes, operador)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (produto_id, tipo, valor_int, razao, observacoes, operador),
        )

        # Atualizar quantidade do item
        conexao.execute(
            """
            UPDATE estoque_itens
            SET quantidade = ?, atualizado_em = CURRENT_TIMESTAMP
            WHERE id_produto = ?
            """,
            (nova_qtd, produto_id),
        )

        conexao.commit()
        conexao.close()
        flash("Movimentação registrada com sucesso!", "sucesso")
        return redirect(url_for("movimentar_estoque"))

    # Se for GET: listar últimas transações
    transacoes = conexao.execute(
        """
        SELECT
            t.id_transacao,
            t.tipo_transacao,
            t.valor,
            t.razao,
            t.observacoes,
            t.operador,
            t.data_registro,
            e.nome_produto
        FROM transacoes_estoque t
        JOIN estoque_itens e ON e.id_produto = t.produto_id
        ORDER BY t.data_registro DESC
        LIMIT 20
        """
    ).fetchall()

    conexao.close()
    return render_template("movimentacoes.html", itens=itens, transacoes=transacoes)

@app.route("/previsao")
def previsao_estoque():
    """
    Mostra, para cada item, a previsão de em quantos dias
    o estoque atual deve acabar, com base no histórico de saídas.
    """
    previsoes = calcular_previsao_estoque()
    return render_template("previsao.html", previsoes=previsoes)

@app.route("/relatorio", methods=["GET", "POST"])
def relatorio_movimentacoes():
    """
    Exibe um relatório filtrado de movimentações por período e item.
    """
    conexao = conectar_banco()

    # Itens para o select
    itens = conexao.execute(
        "SELECT id_produto, nome_produto FROM estoque_itens ORDER BY nome_produto"
    ).fetchall()

    resultados = []
    total_entrada = 0
    total_saida = 0

    if request.method == "POST":
        item_id = request.form.get("item_id")
        inicio = request.form.get("inicio")
        fim = request.form.get("fim")

        query = """
            SELECT
                t.data_registro,
                e.nome_produto,
                t.tipo_transacao,
                t.valor,
                t.razao,
                t.operador
            FROM transacoes_estoque t
            JOIN estoque_itens e ON e.id_produto = t.produto_id
            WHERE 1=1
        """

        params = []

        # filtro por item
        if item_id and item_id != "todos":
            query += " AND t.produto_id = ?"
            params.append(item_id)

        # filtro por data inicial
        if inicio:
            query += " AND date(t.data_registro) >= date(?)"
            params.append(inicio)

        # filtro por data final
        if fim:
            query += " AND date(t.data_registro) <= date(?)"
            params.append(fim)

        query += " ORDER BY t.data_registro DESC"

        resultados = conexao.execute(query, params).fetchall()

        # somatórios
        for r in resultados:
            if r["tipo_transacao"] == "entrada":
                total_entrada += r["valor"]
            else:
                total_saida += r["valor"]

    conexao.close()

    return render_template(
        "relatorio.html",
        itens=itens,
        resultados=resultados,
        total_entrada=total_entrada,
        total_saida=total_saida
    )

if __name__ == "__main__":
    configurar_banco()
    app.run(debug=True)
