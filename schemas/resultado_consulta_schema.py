"""
Schema para ContextoResultadoConsulta — Resultado de Consulta Multisserviço

Responsabilidade:
- Estruturar dados de horários disponíveis encontrados pelo motor
- Persistir resultado com TTL 1h
- Permitir referência ("o primeiro") na mensagem seguinte
- Validar TTL na leitura (não na limpeza agendada)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional
import uuid


@dataclass
class OpcaoHorario:
    """Uma opção de horário disponível encontrada pelo motor"""

    opcao_id: str
    numero: int  # 1, 2, 3 para "o primeiro", "segunda", etc
    profissional_id: str
    data: str  # YYYY-MM-DD
    hora_inicio: str  # HH:MM
    hora_fim: str  # HH:MM
    servicos: list[str]
    duracao_total_min: int

    def to_dict(self) -> dict:
        """Serializar para Firestore"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OpcaoHorario":
        """Desserializar de Firestore"""
        return cls(**data)


@dataclass
class ContextoResultadoConsulta:
    """Resultado persistente de uma consulta multisserviço"""

    # Identificação
    consulta_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    criado_em: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expira_em: str = field(default_factory=lambda: (
        datetime.utcnow() + timedelta(hours=1)
    ).isoformat())

    # Entrada da consulta (para contexto)
    servicos: list[str] = field(default_factory=list)
    data: str = ""  # YYYY-MM-DD
    duracao_total_min: int = 0
    profissional_id: str = ""

    # Resultado da consulta
    opcoes: list[OpcaoHorario] = field(default_factory=list)

    # Seleção (inicialmente vazio)
    opcao_selecionada_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Serializar para Firestore"""
        return {
            "consulta_id": self.consulta_id,
            "criado_em": self.criado_em,
            "expira_em": self.expira_em,
            "servicos": self.servicos,
            "data": self.data,
            "duracao_total_min": self.duracao_total_min,
            "profissional_id": self.profissional_id,
            "opcoes": [o.to_dict() for o in self.opcoes],
            "opcao_selecionada_id": self.opcao_selecionada_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContextoResultadoConsulta":
        """Desserializar de Firestore"""
        opcoes = [
            OpcaoHorario.from_dict(o)
            for o in data.get("opcoes", [])
        ]
        return cls(
            consulta_id=data.get("consulta_id", str(uuid.uuid4())),
            criado_em=data.get("criado_em", datetime.utcnow().isoformat()),
            expira_em=data.get("expira_em", (
                datetime.utcnow() + timedelta(hours=1)
            ).isoformat()),
            servicos=data.get("servicos", []),
            data=data.get("data", ""),
            duracao_total_min=data.get("duracao_total_min", 0),
            profissional_id=data.get("profissional_id", ""),
            opcoes=opcoes,
            opcao_selecionada_id=data.get("opcao_selecionada_id")
        )

    def esta_expirado(self) -> bool:
        """Validar se contexto passou de TTL 1h"""
        try:
            expiracao = datetime.fromisoformat(self.expira_em)
            agora = datetime.utcnow()
            return agora > expiracao
        except Exception as e:
            print(f"[EXPIRE_VALIDATION] ❌ Erro ao validar expiração: {str(e)}", flush=True)
            return True  # Falhar seguro: considerar expirado

    def mapear_referencia_para_numero(self, referencia: str) -> Optional[int]:
        """
        Mapear referências textuais para número de opção (1-indexed).

        Exemplos:
        - "primeiro" → 1
        - "segunda" → 2
        - "última" → len(opcoes)
        """
        ref_norm = referencia.lower().strip()

        # Padrões para primeira opção
        padroes_primeira = [
            "primeiro", "primeira", "1",
            "a primeira", "o primeiro", "primeira opcao", "1a opcao"
        ]
        if ref_norm in padroes_primeira:
            return 1 if self.opcoes else None

        # Padrões para segunda opção
        padroes_segunda = [
            "segundo", "segunda", "2",
            "a segunda", "o segundo", "segunda opcao", "2a opcao"
        ]
        if ref_norm in padroes_segunda:
            return 2 if len(self.opcoes) >= 2 else None

        # Padrões para terceira opção
        padroes_terceira = [
            "terceiro", "terceira", "3",
            "a terceira", "o terceiro", "terceira opcao", "3a opcao"
        ]
        if ref_norm in padroes_terceira:
            return 3 if len(self.opcoes) >= 3 else None

        # Padrões para última opção
        padroes_ultima = [
            "ultimo", "última", "ultima",
            "o ultimo", "a ultima", "a última", "ultima opcao", "última opcao"
        ]
        if ref_norm in padroes_ultima:
            return len(self.opcoes) if self.opcoes else None

        return None

    def obter_opcao(self, numero: int) -> Optional[OpcaoHorario]:
        """
        Obter opção por número (1-indexed).

        Retorna None se número inválido.
        """
        if not isinstance(numero, int):
            return None
        if 1 <= numero <= len(self.opcoes):
            return self.opcoes[numero - 1]
        return None

