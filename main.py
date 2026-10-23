import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from pymongo import MongoClient
from typing import Optional

app = FastAPI(title="API Sistema de Etiquetas")

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("A variável de ambiente MONGO_URI não foi configurada.")

client = MongoClient(MONGO_URI)
db = client["sistema_etiquetas"]
colecao_etiquetas = db["etiquetas"]
colecao_licencas = db["licencas"]


# --- MODELOS DE DADOS ---
class EtiquetaSchema(BaseModel):
    nome: str
    conteudo: str
    conteudo_2: Optional[str] = ""
    pos_x: int = 50
    pos_y: int = 20
    fonte: str = "12,10,8"
    larg_letra: int = 1
    alt_letra: int = 1
    colunas: int = 2
    dist_x: int = 200
    reverso: int = 0
    larg_mm: float = 89.0
    alt_mm: float = 25.0


class LicencaCheckSchema(BaseModel):
    hwid: str
    serial: Optional[str] = None


# --- ENDPOINTS DA API ---

@app.get("/")
def status_api():
    return {"status": "API Online", "banco": "Conectado"}


@app.get("/etiquetas")
def listar_etiquetas(busca: Optional[str] = Query(None)):
    query = {}
    if busca:
        query = {"nome": {"$regex": busca, "$options": "i"}}
    
    etiquetas = list(colecao_etiquetas.find(query, {"_id": 0}))
    return etiquetas


@app.post("/etiquetas")
def salvar_etiqueta(etiqueta: EtiquetaSchema):
    dados = etiqueta.dict()
    colecao_etiquetas.update_one({"nome": dados["nome"]}, {"$set": dados}, upsert=True)
    return {"status": "sucesso", "mensagem": "Etiqueta salva com sucesso!"}


@app.delete("/etiquetas/{nome}")
def deletar_etiqueta(nome: str):
    resultado = colecao_etiquetas.delete_one({"nome": nome})
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Etiqueta não encontrada")
    return {"status": "sucesso", "mensagem": "Etiqueta excluída!"}


@app.post("/licenca/verificar")
def verificar_licenca(payload: LicencaCheckSchema):
    hwid = payload.hwid.strip()
    serial = payload.serial.strip() if payload.serial else None

    if hwid and hwid != "DESCONHECIDO":
        lic_ativa = colecao_licencas.find_one({"hwid": hwid, "status": "ativo"})
        if lic_ativa:
            return {"autorizado": True, "mensagem": "Computador autorizado"}

    if serial:
        licenca = colecao_licencas.find_one({"serial": serial, "status": "ativo"})
        if not licenca:
            return {"autorizado": False, "mensagem": "Chave Serial inválida ou bloqueada!"}

        hwid_banco = licenca.get("hwid", "")

        if not hwid_banco:
            colecao_licencas.update_one({"_id": licenca["_id"]}, {"$set": {"hwid": hwid}})
            return {"autorizado": True, "mensagem": "Ativado com sucesso neste computador!"}
        elif hwid_banco == hwid:
            return {"autorizado": True, "mensagem": "Ativado"}
        else:
            return {"autorizado": False, "mensagem": "Esta Chave Serial pertence a outro computador!"}

    return {"autorizado": False, "mensagem": "Computador não ativado"}
