"""Controller for competition operation records."""

from datetime import datetime, timedelta

from Model.competition_records import (
    Apurado,
    Chegada,
    Classificacao,
    Dorsal,
    Escalao,
    Inscricao,
    RegraApuramento,
    atualizar_classificacao,
    atualizar_dorsal,
    atualizar_chegada,
    atualizar_escalao,
    atualizar_estado_apurado,
    atualizar_inscricao,
    atualizar_regra_apuramento,
    criar_classificacao,
    criar_dorsal,
    criar_chegada,
    criar_escalao,
    criar_inscricao,
    criar_regra_apuramento,
    eliminar_classificacoes,
    eliminar_dorsais,
    eliminar_chegadas,
    eliminar_escalaoes,
    eliminar_inscricoes,
    eliminar_regras_apuramento,
    gerar_apuramentos,
    listar_apurados,
    listar_chegadas,
    listar_classificacoes,
    listar_dorsais,
    listar_escaloes,
    listar_inscricoes,
    listar_regras_apuramento,
)


class CompetitionRecordsController:
    """Coordinates competition record operations between views and models."""

    def listar_inscricoes(self) -> list[Inscricao]:
        return listar_inscricoes()

    def criar_inscricao(
        self,
        idprova: int,
        numeroprocesso: int,
        estado: str,
        indicador_da: bool,
        funcao: str | None,
    ) -> None:
        criar_inscricao(idprova, numeroprocesso, estado, indicador_da, funcao)

    def atualizar_inscricao(
        self,
        idinscricao: int,
        idprova: int,
        numeroprocesso: int,
        estado: str,
        indicador_da: bool,
        funcao: str | None,
    ) -> None:
        atualizar_inscricao(
            idinscricao,
            idprova,
            numeroprocesso,
            estado,
            indicador_da,
            funcao,
        )

    def eliminar_inscricoes(self, ids: list[int]) -> None:
        eliminar_inscricoes(ids)

    def listar_dorsais(self) -> list[Dorsal]:
        return listar_dorsais()

    def criar_dorsal(
        self,
        inscricao_id: int,
        numero: int,
        estado: str,
        entregue_em: datetime | None,
    ) -> int:
        return criar_dorsal(inscricao_id, numero, estado, entregue_em)

    def atualizar_dorsal(
        self,
        iddorsal: int,
        numero: int,
        estado: str,
        entregue_em: datetime | None,
    ) -> None:
        atualizar_dorsal(iddorsal, numero, estado, entregue_em)

    def eliminar_dorsais(self, ids: list[int]) -> None:
        eliminar_dorsais(ids)

    def listar_chegadas(self) -> list[Chegada]:
        return listar_chegadas()

    def criar_chegada(
        self,
        inscricao_id: int,
        tempo_chegada: timedelta,
        metodo: str,
        corrigido_de: int | None,
    ) -> None:
        criar_chegada(inscricao_id, tempo_chegada, metodo, corrigido_de)

    def atualizar_chegada(
        self,
        idchegada: int,
        inscricao_id: int,
        tempo_chegada: timedelta,
        metodo: str,
        corrigido_de: int | None,
    ) -> None:
        atualizar_chegada(
            idchegada,
            inscricao_id,
            tempo_chegada,
            metodo,
            corrigido_de,
        )

    def eliminar_chegadas(self, ids: list[int]) -> None:
        eliminar_chegadas(ids)

    def listar_classificacoes(self) -> list[Classificacao]:
        return listar_classificacoes()

    def criar_classificacao(
        self,
        inscricao_id: int,
        prova_id: int,
        escalao_id: int | None,
        posicao: int,
    ) -> None:
        criar_classificacao(inscricao_id, prova_id, escalao_id, posicao)

    def atualizar_classificacao(
        self,
        idclassificacao: int,
        inscricao_id: int,
        prova_id: int,
        escalao_id: int | None,
        posicao: int,
    ) -> None:
        atualizar_classificacao(
            idclassificacao,
            inscricao_id,
            prova_id,
            escalao_id,
            posicao,
        )

    def eliminar_classificacoes(self, ids: list[int]) -> None:
        eliminar_classificacoes(ids)

    def listar_escaloes(self) -> list[Escalao]:
        return listar_escaloes()

    def criar_escalao(
        self,
        prova_id: int,
        designacao: str,
        sexo: str,
        anonasc_min: int,
        anonasc_max: int,
        da: bool,
    ) -> None:
        criar_escalao(prova_id, designacao, sexo, anonasc_min, anonasc_max, da)

    def atualizar_escalao(
        self,
        idescalao: int,
        prova_id: int,
        designacao: str,
        sexo: str,
        anonasc_min: int,
        anonasc_max: int,
        da: bool,
    ) -> None:
        atualizar_escalao(
            idescalao,
            prova_id,
            designacao,
            sexo,
            anonasc_min,
            anonasc_max,
            da,
        )

    def eliminar_escalaoes(self, ids: list[int]) -> None:
        eliminar_escalaoes(ids)

    def listar_regras_apuramento(self) -> list[RegraApuramento]:
        return listar_regras_apuramento()

    def criar_regra_apuramento(
        self,
        prova_origem_id: int,
        prova_destino_id: int,
        escalao_id: int,
        numero_apurados: int,
    ) -> None:
        criar_regra_apuramento(
            prova_origem_id,
            prova_destino_id,
            escalao_id,
            numero_apurados,
        )

    def atualizar_regra_apuramento(
        self,
        idregra: int,
        prova_origem_id: int,
        prova_destino_id: int,
        escalao_id: int,
        numero_apurados: int,
    ) -> None:
        atualizar_regra_apuramento(
            idregra,
            prova_origem_id,
            prova_destino_id,
            escalao_id,
            numero_apurados,
        )

    def eliminar_regras_apuramento(self, ids: list[int]) -> None:
        eliminar_regras_apuramento(ids)

    def listar_apurados(self, prova_destino_id: int | None = None) -> list[Apurado]:
        return listar_apurados(prova_destino_id)

    def gerar_apuramentos(self, prova_destino_id: int) -> int:
        return gerar_apuramentos(prova_destino_id)

    def atualizar_estado_apurado(
        self,
        inscricao_id: int,
        prova_destino_id: int,
        estado: str,
    ) -> None:
        atualizar_estado_apurado(inscricao_id, prova_destino_id, estado)
