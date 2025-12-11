import json

class SimuladorDeFi:
    def __init__(self):
        # Configurações
        self.TARGET_LTV = 0.75
        self.MAX_LTV_RISCO = 0.82
        self.TAXA_PLATAFORMA = 0.001
        
        # Estado
        self.supply = 0.0
        self.borrow = 0.0
        self.wallet = 0.0
        self.target_supply = 0.0
        self.target_wallet = 0.0
        
        # Controle
        self.supply_acumulado = 0.0
        self.ciclos = 0
        self.log_txt = []
        self.log_json = []

    def carregar_dados(self):
        print(f"{'='*60}")
        print("SIMULADOR MULTI-ESTRATÉGIA (MODULAR & BLINDADO)")
        print(f"{'='*60}\n")
        try:
            self.supply = float(input("Supply inicial: "))
            self.borrow = float(input("Borrow inicial: "))
            self.wallet = float(input("Saldo disponivel na wallet: "))
            self.target_supply = float(input("Supply final desejado: "))
            
            w_target = input("Wallet final desejada (Opcional, Enter p/ 0): ")
            self.target_wallet = float(w_target) if w_target else 99999999.0
            
        except ValueError:
            print("Erro: Números inválidos.")
            exit()

    # ====================== ESTRATÉGIAS ======================

    def _estrategia_1_sacar_lucro(self):
        op_supply = self.supply_acumulado
        
        capacidade_total = (self.supply + op_supply) * self.TARGET_LTV
        op_borrow = max(0, capacidade_total - self.borrow)
        
        return {
            "supply": op_supply,
            "borrow": op_borrow,
            "repay": 0.0,
            "reinvest": 0.0,
            "lucro_sacado": op_borrow,
            "nome": "Estratégia 1 (Sacar Lucro)"
        }

    def _estrategia_3_flash_loan(self):
        """Tenta alavancagem máxima via Flash Loan."""
        # Calcular salto ideal
        capacidade_total = (self.supply + self.supply_acumulado) / (1 - self.TARGET_LTV)
        capacidade_total = min(capacidade_total, self.target_supply)
        
        delta_supply = max(0, capacidade_total - self.supply)
        novo_borrow_total = capacidade_total * self.TARGET_LTV
        delta_borrow = max(0, novo_borrow_total - self.borrow)
        
        taxas_estimadas = (delta_borrow + delta_supply) * self.TAXA_PLATAFORMA
        lucro_bruto = delta_borrow - delta_supply
        
        # Verifica viabilidade
        pode_pagar_com_lucro = lucro_bruto > taxas_estimadas
        pode_pagar_com_wallet = self.wallet > (taxas_estimadas - lucro_bruto)
        
        if delta_supply > 0.001 and (pode_pagar_com_lucro or pode_pagar_com_wallet):
            return {
                "supply": 0.0,
                "borrow": delta_borrow,
                "repay": 0.0,
                "reinvest": delta_supply,
                "lucro_sacado": lucro_bruto, 
                "nome": "Estratégia 3 (Flash Loan Agressivo)"
            }
        else:
            # Fallback para estratégia conservadora
            print(f"  > [AVISO] Flash Loan caro demais. Ativando Plano B (Formiguinha)...")
            return self._estrategia_5_reinvestir_acumulado(fallback=True)

    def _estrategia_5_reinvestir_acumulado(self, fallback=False):
        nome = "Estratégia 5 (Passo de Formiga)" if fallback else "Estratégia 5 (Reinvestir)"
        
        op_supply = self.supply_acumulado
        
        # Se for fallback e não tiver acumulado, usa a wallet
        if fallback and op_supply == 0 and self.wallet > 0:
            op_supply = self.wallet * 0.90
            
        return {
            "supply": op_supply,
            "borrow": 0.0,
            "repay": 0.0,
            "reinvest": 0.0,
            "lucro_sacado": 0.0,
            "nome": nome
        }

    def _estrategia_7_repagar_inteligente(self):
        caixa_total = self.supply_acumulado + self.wallet
        
        # Reserva dinheiro para a taxa com folga
        valor_maximo_repagavel = caixa_total / (1 + self.TAXA_PLATAFORMA * 1.5)
        
        op_repay = min(self.borrow, valor_maximo_repagavel)
        
        if op_repay < 0.0001: op_repay = 0.0
            
        return {
            "supply": 0.0, 
            "borrow": 0.0,
            "repay": op_repay,
            "reinvest": 0.0,
            "lucro_sacado": 0.0, 
            "nome": "Estratégia 7 (Repagamento Seguro)"
        }
    # ====================== MOTOR DE DECISÃO ======================

    def decidir_proximo_passo(self):
        ltv = self.borrow / self.supply if self.supply > 0 else 0
        falta_supply = self.target_supply - self.supply
        
        # 1. Risco Crítico
        if ltv > self.MAX_LTV_RISCO:
            return self._estrategia_7_repagar_inteligente()
        
        # 2. Fase de Crescimento (Longe da meta + Margem saudável)
        if falta_supply > (self.supply * 0.05) and ltv < self.TARGET_LTV:
            return self._estrategia_3_flash_loan()
            
        # 3. Fase de Lucro/Estabilidade
        if ltv < self.TARGET_LTV:
            return self._estrategia_1_sacar_lucro()
            
        # 4. Estagnação (LTV cheio)
        if self.supply_acumulado > 0:
            return self._estrategia_5_reinvestir_acumulado()
            
        # 5. Tentativa Final (Espremer a wallet)
        return self._estrategia_1_sacar_lucro()

    def executar_ciclo(self):
        self.ciclos += 1
        
        # Análise prévia
        ltv_pre = (self.borrow / self.supply * 100) if self.supply > 0 else 0
        falta_meta = max(0, self.target_supply - self.supply)
        
        plano = self.decidir_proximo_passo()
        
        # Recuperar valores
        op_supply = plano['supply']
        op_borrow = plano['borrow']
        op_repay = plano['repay']
        op_reinvest = plano['reinvest']
        op_lucro_sacado = plano['lucro_sacado']
        
        # Consumir acumulado
        supply_usado_neste_ciclo = self.supply_acumulado if plano['nome'] != "Estratégia 3" else 0
        self.supply_acumulado = 0 
        
        # Cálculos financeiros
        volume_total = op_borrow + op_repay + op_reinvest + op_supply
        taxas = volume_total * self.TAXA_PLATAFORMA
        
        # Separação visual de taxas
        taxa_flash_est = 0.0
        if "Flash Loan" in plano['nome']:
            taxa_flash_est = taxas * 0.9
            
        delta_wallet = op_lucro_sacado - taxas
        
        # Ajuste para repagamento
        if plano['nome'] == "Estratégia 7 (Repagamento Seguro)":
            custo_repay = max(0, op_repay - supply_usado_neste_ciclo)
            delta_wallet -= custo_repay

        # Verificação de segurança
        if self.wallet + delta_wallet < -0.00000001:
            print(f"  > [CRÍTICO] Abortar ciclo {self.ciclos}. Wallet insuficiente.")
            self.supply_acumulado = supply_usado_neste_ciclo
            return False 
        
        # COMMIT
        old_wallet = self.wallet
        self.wallet += delta_wallet
        self.supply += (op_supply + op_reinvest)
        self.borrow += op_borrow
        self.borrow -= op_repay
        
        if plano['nome'] not in ["Estratégia 1 (Sacar Lucro)", "Estratégia 3 (Flash Loan Agressivo)"]:
             self.supply_acumulado += max(0, delta_wallet)

        # Logs
        ltv_pos = (self.borrow / self.supply * 100) if self.supply > 0 else 0
        saude = (self.supply * 0.74) / self.borrow if self.borrow > 0 else 999.0
        
        log_denso = (
            f"\n{'='*80}\n"
            f"CICLO {self.ciclos:03d} | ESTRATÉGIA: {plano['nome'].upper()}\n"
            f"{'-'*80}\n"
            f"[1] ANÁLISE DE CENÁRIO\n"
            f"    > LTV Inicial:        {ltv_pre:.4f}%\n"
            f"    > Distância Meta:     {falta_meta:.8f} BTC\n"
            f"    > Caixa Disponível:   {old_wallet:.8f} BTC\n"
            f"\n"
            f"[2] EXECUÇÃO DA ESTRATÉGIA\n"
            f"    > Supply Reciclado:   {supply_usado_neste_ciclo:.8f} (Do Acumulado)\n"
            f"    > Supply Novo/Flash:  {op_reinvest:.8f}\n"
            f"    > Novo Empréstimo:    {op_borrow:.8f}\n"
            f"    > Repagamento Dívida: {op_repay:.8f}\n"
            f"\n"
            f"[3] CUSTOS E TAXAS (Discriminação)\n"
            f"    > Volume Transação:   {volume_total:.8f}\n"
            f"    > Taxa Plataforma:    {taxas - taxa_flash_est:.8f}\n"
            f"    > Taxa Flash Loan:    {taxa_flash_est:.8f}\n"
            f"    > TOTAL TAXAS:        -{taxas:.8f}\n"
            f"\n"
            f"[4] RESULTADO CONTÁBIL\n"
            f"    > Lucro Bruto Op:     {op_lucro_sacado:.8f}\n"
            f"    > Variação Wallet:    {delta_wallet:.8f}\n"
            f"    > Acumulado Próx.:    {self.supply_acumulado:.8f}\n"
            f"{'-'*80}\n"
            f"[5] ESTADO FINAL DO SISTEMA\n"
            f"    > SUPPLY TOTAL:       {self.supply:.8f}\n"
            f"    > BORROW TOTAL:       {self.borrow:.8f}\n"
            f"    > WALLET TOTAL:       {self.wallet:.8f}\n"
            f"    > LTV FINAL:          {ltv_pos:.4f}%\n"
            f"    > SAÚDE (HF):         {saude:.4f}\n"
            f"{'='*80}\n"
        )
        
        print(log_denso)
        self.log_txt.append(log_denso)
        
        self.log_json.append({
            "Ciclo": self.ciclos,
            "Estrategia": plano['nome'],
            "Detalhes": {
                "Supply_Inicial": f"{self.supply - op_supply - op_reinvest:.8f}",
                "Novo_Borrow": f"{op_borrow:.8f}",
                "Reinvestimento": f"{op_reinvest:.8f}",
                "Taxas": f"{taxas:.8f}",
                "Wallet_Variation": f"{delta_wallet:.8f}"
            },
            "Estado_Final": {
                "Supply": f"{self.supply:.8f}",
                "Borrow": f"{self.borrow:.8f}",
                "Wallet": f"{self.wallet:.8f}",
                "LTV": f"{ltv_pos:.2f}%"
            }
        })
        
        if op_supply == 0 and op_borrow == 0 and op_repay == 0 and op_reinvest == 0:
            print("--- SISTEMA ESTAGNADO: SEM MARGEM PARA OPERAR ---")
            return "STOP"
            
        return True

    def rodar(self):
        self.carregar_dados()
        print("\n--- INICIANDO MOTOR DE DECISÃO ---\n")
        
        while (self.supply < self.target_supply or self.wallet < self.target_wallet) and self.ciclos < 15:
            resultado = self.executar_ciclo()
            if resultado == "STOP":
                break
                
        self.gerar_relatorios()

    def gerar_relatorios(self):
        resultado_final = (
            f"\n{'#'*80}\n"
            f"RELATÓRIO DE CONSOLIDAÇÃO FINAL (BITCOIN STANDARD)\n"
            f"{'#'*80}\n"
            f"METAS:\n"
            f"  > Supply Alvo:     {self.target_supply:.8f}\n"
            f"  > Wallet Alvo:     {self.target_wallet:.8f}\n"
            f"\nRESULTADOS:\n"
            f"  > Supply Final:    {self.supply:.8f}\n"
            f"  > Borrow Final:    {self.borrow:.8f}\n"
            f"  > Wallet Final:    {self.wallet:.8f}\n"
            f"\nPERFORMANCE:\n"
            f"  > Total Ciclos:    {self.ciclos}\n"
            f"  > Status Meta:     {'[SUCESSO]' if self.supply >= self.target_supply else '[PARCIAL]'}\n"
            f"{'#'*80}\n"
        )

        print(resultado_final)
        
        with open("resultado_operacoes_denso.txt", "a", encoding='utf-8') as f:
            for linha in self.log_txt:
                f.write(linha)
            f.write(resultado_final)
                
        with open("operacoes_denso.json", "a", encoding='utf-8') as f:
            json.dump(self.log_json, f, indent=4)
        print("\nArquivos de log denso gerados: 'resultado_operacoes_denso.txt' e 'operacoes_denso.json'")

# ====================== TESTES AUTOMÁTICOS ======================

class SimuladorAutomatico(SimuladorDeFi):
    def __init__(self, dados_cenario):
        super().__init__()
        self.dados_teste = dados_cenario

    def carregar_dados(self):
        print(f"\n{'>'*20} INICIANDO TESTE AUTOMÁTICO: {self.dados_teste['nome']} {'<'*20}")
        self.supply = float(self.dados_teste['supply'])
        self.borrow = float(self.dados_teste['borrow'])
        self.wallet = float(self.dados_teste['wallet'])
        self.target_supply = float(self.dados_teste['target_supply'])
        self.target_wallet = float(self.dados_teste['target_wallet'])

def rodar_bateria_testes():
    # 1. Limpar o arquivo de log antigo antes de começar
    with open("resultado_operacoes_denso.txt", "w", encoding='utf-8') as f:
        f.write("=== LOG DE AUDITORIA COMPLETA (TODOS OS CENÁRIOS) ===\n\n")

    # LISTA DE CENÁRIOS
    cenarios = [
        {
            "nome": "CENÁRIO 1: O Salto Perfeito (Flash Loan)",
            "supply": 0.1,
            "borrow": 0,
            "wallet": 0.01,
            "target_supply": 0.35,
            "target_wallet": 0
        },
        {
            "nome": "CENÁRIO 2: A Formiguinha (Resiliência)",
            "supply": 0.5,
            "borrow": 0.37, 
            "wallet": 0.005,
            "target_supply": 0.8,
            "target_wallet": 0
        },
        {
            "nome": "CENÁRIO 3: O Bombeiro (Salvar Risco)",
            "supply": 1.0,
            "borrow": 0.83, 
            "wallet": 0.5,
            "target_supply": 2.0,
            "target_wallet": 0
        },
        {
            "nome": "CENÁRIO 4: A Caixa Registradora (Extrair Lucro)",
            "supply": 10.0,
            "borrow": 0,
            "wallet": 0,
            "target_supply": 10.0,
            "target_wallet": 5.0
        },
        {
            "nome": "CENÁRIO 5: O Impossível (Sem saldo pra taxa)",
            "supply": 1.0,
            "borrow": 0,
            "wallet": 0, 
            "target_supply": 5.0,
            "target_wallet": 0
        },
        {
            "nome": "CENÁRIO 6: O Estagnado (Sem margem pra operar)",
            "supply": 2.0,
            "borrow": 1.5,
            "wallet": 0.0001,
            "target_supply": 3.0,
            "target_wallet": 0
        },
        {
            "nome": "CENÁRIO 7: Pedida do Cliente (Wallet Zerada)",
            "supply": 1,
            "borrow": 0,
            "wallet": 0,
            "target_supply": 10,
            "target_wallet": 0
        }
    ]

    print(f"--- INICIANDO BATERIA DE {len(cenarios)} TESTES ---\n")

    for i, dados in enumerate(cenarios):
        # Escreve um separador no arquivo para ficar bonito
        with open("resultado_operacoes_denso.txt", "a", encoding='utf-8') as f:
            f.write(f"\n\n{'='*80}\n")
            f.write(f"TESTE {i+1}: {dados['nome'].upper()}\n")
            f.write(f"{'='*80}\n")

        print(f"\n>>>>>>>> INICIANDO: {dados['nome']} <<<<<<<<")
        bot = SimuladorAutomatico(dados)
        bot.rodar()
        print(f"[FIM DO {dados['nome']}]")

if __name__ == "__main__":
    rodar_bateria_testes()
