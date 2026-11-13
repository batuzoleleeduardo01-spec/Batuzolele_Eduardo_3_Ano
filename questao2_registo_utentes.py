import hashlib
import json
import os
import re
from datetime import datetime

FICHEIRO = "utentes.json"

# Permissões por perfil
PERMISSOES = {
    "admin":      {"registar", "editar", "ver_pessoais", "ver_historico"},
    "recepcao":   {"registar", "editar", "ver_pessoais"},
    "enfermeiro": {"ver_pessoais", "ver_historico"},
    "medico":     {"ver_pessoais", "ver_historico", "add_consulta"},
}


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


# Utilizadores de demonstração (alterar em produção)
UTILIZADORES = {
    "admin":  {"senha": h("admin123"),  "perfil": "admin",      "nome": "Administrador"},
    "recep":  {"senha": h("recep123"),  "perfil": "recepcao",   "nome": "Recepção"},
    "enf":    {"senha": h("enf123"),    "perfil": "enfermeiro", "nome": "Enfermeiro(a)"},
    "medico": {"senha": h("medico123"), "perfil": "medico",     "nome": "Dr(a). Médico"},
}


def carregar():
    if os.path.exists(FICHEIRO):
        with open(FICHEIRO, encoding="utf-8") as f:
            return json.load(f)
    return {"contador": 0, "utentes": {}}


def guardar(db):
    with open(FICHEIRO, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def ler_texto(msg, obrigatorio=True):
    while True:
        t = input(msg).strip()
        if t or not obrigatorio:
            return t
        print("  Campo obrigatório.")


def ler_data(msg, permitir_futuro=False):
    while True:
        t = input(msg + " (dd/mm/aaaa): ").strip()
        try:
            d = datetime.strptime(t, "%d/%m/%Y")
            if not permitir_futuro and d > datetime.now():
                print("  A data não pode ser futura.")
                continue
            return d.strftime("%d/%m/%Y")
        except ValueError:
            print("  Data inválida.")


def validar_nif(nif):
    return bool(re.fullmatch(r"[A-Za-z0-9]{9,14}", nif))


def login():
    print("\n===== REGISTO ELETRÓNICO DE UTENTES =====")
    for _ in range(3):
        u = input("Utilizador: ").strip()
        s = input("Palavra-passe: ").strip()
        if u in UTILIZADORES and UTILIZADORES[u]["senha"] == h(s):
            print(f"Bem-vindo(a), {UTILIZADORES[u]['nome']} [{UTILIZADORES[u]['perfil']}]")
            return UTILIZADORES[u]
        print("Credenciais inválidas.")
    return None


def autorizado(user, perm):
    if perm in PERMISSOES[user["perfil"]]:
        return True
    print("  Acesso negado para o seu perfil.")
    return False


def registar_utente(db, user):
    if not autorizado(user, "registar"):
        return
    print("\n--- Novo Utente ---")
    nome = ler_texto("Nome completo: ")
    nasc = ler_data("Data de nascimento")
    while True:
        g = input("Género (M/F): ").strip().upper()
        if g in ("M", "F"):
            break
    morada = ler_texto("Morada: ")
    telefone = ler_texto("Telefone: ", obrigatorio=False)

    nif = ""
    if input("Tem NIF a associar? (s/n): ").strip().lower() == "s":
        while True:
            nif = input("NIF: ").strip().upper()
            if not validar_nif(nif):
                print("  NIF inválido (9 a 14 caracteres alfanuméricos).")
            elif any(u["nif"] == nif for u in db["utentes"].values()):
                print("  Este NIF já está associado a outro utente.")
            else:
                break

    db["contador"] += 1
    num = f"UT-{db['contador']:06d}"
    db["utentes"][num] = {
        "numero": num, "nome": nome, "nascimento": nasc, "genero": g,
        "morada": morada, "telefone": telefone, "nif": nif,
        "registado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "historico": [],
    }
    guardar(db)
    print(f"\nUtente registado. Número de registo eletrónico: {num}")


def obter(db):
    num = input("Número de registo (ex.: UT-000001): ").strip().upper()
    u = db["utentes"].get(num)
    if not u:
        print("  Utente não encontrado.")
    return u


def consultar_dados(db, user):
    if not autorizado(user, "ver_pessoais"):
        return
    u = obter(db)
    if not u:
        return
    print("\n--- Dados do Utente ---")
    print(f"Nº registo : {u['numero']}")
    print(f"Nome       : {u['nome']}")
    print(f"Nascimento : {u['nascimento']}   Género: {u['genero']}")
    print(f"Morada     : {u['morada']}   Tel.: {u['telefone'] or '-'}")
    print(f"NIF        : {u['nif'] or 'não associado'}")
    print(f"Consultas  : {len(u['historico'])}")


def editar_utente(db, user):
    if not autorizado(user, "editar"):
        return
    u = obter(db)
    if not u:
        return
    novo = input(f"Nova morada [{u['morada']}]: ").strip()
    tel = input(f"Novo telefone [{u['telefone']}]: ").strip()
    if novo:
        u["morada"] = novo
    if tel:
        u["telefone"] = tel
    guardar(db)
    print("Dados atualizados.")


def adicionar_consulta(db, user):
    if not autorizado(user, "add_consulta"):
        return
    u = obter(db)
    if not u:
        return
    print(f"Consulta para {u['nome']}")
    u["historico"].append({
        "data": ler_data("Data da consulta"),
        "motivo": ler_texto("Motivo: "),
        "diagnostico": ler_texto("Diagnóstico: "),
        "tratamento": ler_texto("Tratamento/prescrição: ", obrigatorio=False),
        "observacoes": ler_texto("Observações: ", obrigatorio=False),
        "profissional": user["nome"],
    })
    guardar(db)
    print("Consulta registada no histórico clínico.")


def ver_historico(db, user):
    if not autorizado(user, "ver_historico"):
        return
    u = obter(db)
    if not u:
        return
    print(f"\n--- Histórico clínico de {u['nome']} ({u['numero']}) ---")
    if not u["historico"]:
        print("Sem consultas registadas.")
    for i, c in enumerate(sorted(u["historico"], key=lambda x: datetime.strptime(x["data"], "%d/%m/%Y")), 1):
        print(f"{i}. {c['data']} | {c['motivo']}")
        print(f"   Diagnóstico: {c['diagnostico']}")
        if c["tratamento"]:
            print(f"   Tratamento : {c['tratamento']}")
        if c["observacoes"]:
            print(f"   Obs.       : {c['observacoes']}")
        print(f"   Profissional: {c['profissional']}")


def pesquisar_nome(db, user):
    if not autorizado(user, "ver_pessoais"):
        return
    t = input("Parte do nome: ").strip().lower()
    for u in db["utentes"].values():
        if t in u["nome"].lower():
            print(f"{u['numero']} - {u['nome']}")


def main():
    db = carregar()
    user = login()
    if not user:
        print("Acesso bloqueado.")
        return
    acoes = {
        "1": ("Registar novo utente", registar_utente),
        "2": ("Consultar dados do utente (por nº de registo)", consultar_dados),
        "3": ("Editar contactos", editar_utente),
        "4": ("Adicionar consulta ao histórico", adicionar_consulta),
        "5": ("Ver histórico clínico", ver_historico),
        "6": ("Pesquisar por nome", pesquisar_nome),
    }
    while True:
        print("\n--- MENU ---")
        for k, (t, _) in acoes.items():
            print(f" {k} - {t}")
        print(" 0 - Sair")
        op = input("Opção: ").strip()
        if op == "0":
            break
        if op in acoes:
            acoes[op][1](db, user)
        else:
            print("Opção inválida.")


if __name__ == "__main__":
    main()
