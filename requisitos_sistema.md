# Sistema de Armazenamento de Materiais de Papelaria

## Objetivo
Controlar o estoque de materiais de papelaria (canetas, cadernos, pastas, grampos, clips, folhas, etc.), registrando entradas e saídas, acompanhando a quantidade disponível de cada item, gerando relatórios de movimentação e prevendo quando o estoque de um item irá se esgotar.

## Usuários
- Funcionário da papelaria
- Gerente

## Funcionalidades obrigatórias

1. **Cadastro de materiais**
   - Nome do material
   - Categoria (ex.: escrita, organização, papel, etc.)
   - Unidade de medida (ex.: unidades, caixas, pacotes)
   - Quantidade inicial em estoque
   - Localização (ex.: prateleira, gaveta, setor)
   - Observações (opcional)

2. **Listagem de materiais**
   - Listar todos os materiais cadastrados
   - Permitir buscar/filtrar por nome e/ou categoria

3. **Movimentação de estoque**
   - **Entrada de itens** (quando chega novo estoque)
     - Registro de data, quantidade e, se necessário, observação (ex.: motivo da entrada)
   - **Saída de itens** (quando é vendido/retirado)
     - Registro de data, quantidade e motivo (ex.: venda, uso interno)
   - Atualização automática da quantidade atual em estoque após cada movimentação

4. **Consulta de estoque**
   - Exibir a quantidade atual de cada material
   - Indicar claramente quando um item estiver com quantidade **abaixo de um nível mínimo** configurado (ex.: “estoque baixo”)

5. **Relatórios de movimentação**
   - Relatório simples de entradas e saídas por período (ex.: por dia, semana ou mês)
   - Possibilidade de visualizar o histórico de movimentação de um item específico

6. **Previsão de esgotamento de estoque**
   - Com base no histórico de saídas de cada material (consumo ao longo do tempo), calcular uma **média de consumo**.
   - Estimar **em quantos dias o estoque atual deve acabar**, considerando essa média.
   - Destacar itens com previsão de esgotamento em curto prazo (ex.: “este item pode acabar em X dias”).

## Possíveis melhorias futuras (não obrigatórias neste trabalho)
- Controle de acesso por usuário (login e senha).
- Telas específicas para gerente com visão consolidada de relatórios.
