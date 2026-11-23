"""Read-only sample data for the database-free demonstration mode."""

from datetime import date, datetime, time, timedelta
from typing import NoReturn

from Controllers.alunos_turmas_controller import AlunosTurmasController
from Controllers.competition_records_controller import (
    CompetitionRecordsController,
)
from Controllers.provas_controller import ProvasController
from Model.alunos_turmas import Aluno, Turma
from Model.competition_records import (
    Apurado,
    Chegada,
    Classificacao,
    Dorsal,
    Escalao,
    Inscricao,
    RegraApuramento,
)
from Model.provas import Prova


def _read_only() -> NoReturn:
    raise RuntimeError("The demonstration is read-only.")


class DemoData:
    """Related sample records shared by the read-only demo controllers."""

    def __init__(self) -> None:
        today = date.today()
        self.provas = [
            Prova(
                1,
                "2026/2027",
                "Porto",
                "Escola Básica do Vale",
                today - timedelta(days=30),
                time(9, 0),
                time(12, 0),
            ),
            Prova(
                2,
                "2026/2027",
                "Matosinhos",
                "Escola Secundária da Praia",
                today - timedelta(days=10),
                time(9, 30),
                time(12, 30),
            ),
            Prova(
                3,
                "2026/2027",
                "Porto",
                "Escola Básica do Vale",
                today + timedelta(days=7),
                time(9, 0),
                time(12, 0),
            ),
            Prova(
                4,
                "2026/2027",
                "Maia",
                "Escola Básica da Maia",
                today + timedelta(days=21),
                time(10, 0),
                time(13, 0),
            ),
        ]
        self.turmas = [
            Turma(1, 5, "A", 2),
            Turma(2, 6, "B", 2),
        ]
        self.alunos = [
            Aluno(1001, "Beatriz Almeida", date(today.year - 13, 4, 12), "F", 1, "5.º A"),
            Aluno(1002, "Diogo Costa", date(today.year - 12, 8, 3), "M", 1, "5.º A"),
            Aluno(1003, "Inês Ferreira", date(today.year - 12, 2, 21), "F", 2, "6.º B"),
            Aluno(1004, "Rafael Gomes", date(today.year - 11, 11, 9), "M", 2, "6.º B"),
        ]
        self.inscricoes = [
            Inscricao(
                1, 1, 1001, "participante", False, None, "Beatriz Almeida",
                self.prova_label(1), datetime.now() - timedelta(days=34),
            ),
            Inscricao(
                2, 1, 1002, "participante", False, None, "Diogo Costa",
                self.prova_label(1), datetime.now() - timedelta(days=34),
            ),
            Inscricao(
                3, 2, 1003, "participante", True, None, "Inês Ferreira",
                self.prova_label(2), datetime.now() - timedelta(days=14),
            ),
            Inscricao(
                4, 3, 1004, "participante", False, None, "Rafael Gomes",
                self.prova_label(3), datetime.now() - timedelta(days=2),
            ),
        ]
        self.dorsais = [
            Dorsal(1, 1, 101, "devolvido", None, "Beatriz Almeida", 1001, self.prova_label(1)),
            Dorsal(2, 2, 102, "devolvido", None, "Diogo Costa", 1002, self.prova_label(1)),
            Dorsal(
                3, 3, 201, "entregue", datetime.now() - timedelta(days=10),
                "Inês Ferreira", 1003, self.prova_label(2),
            ),
            Dorsal(4, 4, 301, "atribuido", None, "Rafael Gomes", 1004, self.prova_label(3)),
        ]
        self.chegadas = [
            Chegada(
                1, 1, timedelta(minutes=72),
                "manual", None, "Beatriz Almeida", 1001, self.prova_label(1), 101,
            ),
            Chegada(
                2, 2, timedelta(minutes=74),
                "qrcode", None, "Diogo Costa", 1002, self.prova_label(1), 102,
            ),
            Chegada(
                3, 3, timedelta(minutes=48),
                "manual", None, "Inês Ferreira", 1003, self.prova_label(2), 201,
            ),
        ]
        self.escaloes = [
            Escalao(
                1, 1, "Infantis femininos", "F", today.year - 14,
                today.year - 13, False, self.prova_label(1),
            ),
            Escalao(
                2, 2, "Infantis femininos", "F", today.year - 13,
                today.year - 12, False, self.prova_label(2),
            ),
            Escalao(
                3, 1, "Infantis masculinos", "M", today.year - 14,
                today.year - 12, False, self.prova_label(1),
            ),
        ]
        self.classificacoes = [
            Classificacao(
                1, 1, 1, 1, 1, "Beatriz Almeida", 1001,
                self.prova_label(1), "Infantis femininos",
            ),
            Classificacao(
                2, 2, 1, 3, 2, "Diogo Costa", 1002,
                self.prova_label(1), "Infantis masculinos",
            ),
            Classificacao(
                3, 3, 2, 2, 1, "Inês Ferreira", 1003,
                self.prova_label(2), "Infantis femininos",
            ),
        ]
        self.regras_apuramento = [
            RegraApuramento(
                1, 1, 3, 1, 1, self.prova_label(1), self.prova_label(3),
                "Infantis femininos",
            ),
        ]
        self.apurados = [
            Apurado(
                1, 3, 1, "confirmado", "Beatriz Almeida", 1001,
                self.prova_label(3), self.prova_label(1), "Infantis femininos", 1,
            ),
        ]

    def prova_label(self, prova_id: int) -> str:
        prova = next(prova for prova in self.provas if prova.idprova == prova_id)
        return f"{prova.escola} · {prova.data.strftime('%d/%m/%Y')}"

    def upcoming_prova_ids(self) -> set[int]:
        today = date.today()
        return {
            prova.idprova
            for prova in self.provas
            if prova.data >= today
        }


class DemoProvasController(ProvasController):
    """Provides sample events and counts without accessing MySQL."""

    def __init__(self, data: DemoData) -> None:
        self._data = data

    def listar_provas(self) -> list[Prova]:
        upcoming_prova_ids = self._data.upcoming_prova_ids()
        return sorted(
            [
                prova for prova in self._data.provas
                if prova.idprova in upcoming_prova_ids
            ],
            key=lambda prova: (prova.data, prova.horainicio),
        )

    def contar_alunos_inscritos(self, idprova: int) -> int:
        return sum(
            inscricao.idprova == idprova
            and inscricao.estado in {"inscrito", "participante"}
            for inscricao in self._data.inscricoes
        )

    def criar_prova(
        self,
        anolectivo: str,
        concelho: str,
        escola: str,
        data: date,
        horainicio: time,
        horafinal: time,
    ) -> None:
        _read_only()

    def atualizar_prova(
        self,
        idprova: int,
        anolectivo: str,
        concelho: str,
        escola: str,
        data: date,
        horainicio: time,
        horafinal: time,
    ) -> None:
        _read_only()

    def eliminar_provas(self, ids_provas: list[int]) -> None:
        _read_only()


class DemoAlunosTurmasController(AlunosTurmasController):
    """Provides sample students and classes without accessing MySQL."""

    def __init__(self, data: DemoData) -> None:
        self._data = data

    def listar_alunos(
        self,
        pesquisa: str = "",
        turma_id: int | None = None,
    ) -> list[Aluno]:
        query = pesquisa.strip().casefold()
        return [
            aluno
            for aluno in self._data.alunos
            if (turma_id is None or aluno.turma_id == turma_id)
            and (
                not query
                or query in aluno.nome.casefold()
                or query in f"{aluno.numeroprocesso:05d}"
            )
        ]

    def listar_turmas(self) -> list[Turma]:
        return list(self._data.turmas)

    def criar_aluno(
        self,
        numeroprocesso: int,
        nome: str,
        datanasc: date,
        sexo: str,
        turma_id: int | None,
    ) -> None:
        _read_only()

    def atualizar_aluno(
        self,
        numeroprocesso: int,
        nome: str,
        datanasc: date,
        sexo: str,
        turma_id: int | None,
    ) -> None:
        _read_only()

    def criar_turma(self, ano_escolar: int, letra: str) -> None:
        _read_only()

    def atualizar_turma(
        self,
        id_turma: int,
        ano_escolar: int,
        letra: str,
    ) -> None:
        _read_only()

    def eliminar_alunos(self, numeros_processo: list[int]) -> None:
        _read_only()

    def eliminar_turmas(self, ids_turmas: list[int]) -> None:
        _read_only()


class DemoCompetitionRecordsController(CompetitionRecordsController):
    """Provides sample competition records without accessing MySQL."""

    def __init__(self, data: DemoData) -> None:
        self._data = data

    def listar_inscricoes(self) -> list[Inscricao]:
        upcoming_prova_ids = self._data.upcoming_prova_ids()
        return [
            inscricao
            for inscricao in self._data.inscricoes
            if inscricao.idprova in upcoming_prova_ids
        ]

    def listar_dorsais(self) -> list[Dorsal]:
        upcoming_prova_ids = self._data.upcoming_prova_ids()
        upcoming_inscricao_ids = {
            inscricao.id
            for inscricao in self._data.inscricoes
            if inscricao.idprova in upcoming_prova_ids
        }
        return [
            dorsal for dorsal in self._data.dorsais
            if dorsal.inscricao_id in upcoming_inscricao_ids
        ]

    def listar_chegadas(self) -> list[Chegada]:
        upcoming_prova_ids = self._data.upcoming_prova_ids()
        upcoming_inscricao_ids = {
            inscricao.id
            for inscricao in self._data.inscricoes
            if inscricao.idprova in upcoming_prova_ids
        }
        return [
            chegada for chegada in self._data.chegadas
            if chegada.inscricao_id in upcoming_inscricao_ids
        ]

    def listar_classificacoes(self) -> list[Classificacao]:
        upcoming_prova_ids = self._data.upcoming_prova_ids()
        return [
            classificacao
            for classificacao in self._data.classificacoes
            if classificacao.prova_id in upcoming_prova_ids
        ]

    def listar_escaloes(self) -> list[Escalao]:
        upcoming_prova_ids = self._data.upcoming_prova_ids()
        return [
            escalao for escalao in self._data.escaloes
            if escalao.prova_id in upcoming_prova_ids
        ]

    def listar_regras_apuramento(self) -> list[RegraApuramento]:
        upcoming_prova_ids = self._data.upcoming_prova_ids()
        return [
            regra for regra in self._data.regras_apuramento
            if regra.prova_origem_id in upcoming_prova_ids
            and regra.prova_destino_id in upcoming_prova_ids
        ]

    def listar_apurados(self, prova_destino_id: int | None = None) -> list[Apurado]:
        upcoming_prova_ids = self._data.upcoming_prova_ids()
        upcoming_classificacao_ids = {
            classificacao.id
            for classificacao in self._data.classificacoes
            if classificacao.prova_id in upcoming_prova_ids
        }
        return [
            apurado
            for apurado in self._data.apurados
            if apurado.prova_destino_id in upcoming_prova_ids
            and apurado.classificacao_id in upcoming_classificacao_ids
            and (
                prova_destino_id is None
                or apurado.prova_destino_id == prova_destino_id
            )
        ]

    def criar_inscricao(
        self,
        idprova: int,
        numeroprocesso: int,
        estado: str,
        indicador_da: bool,
        funcao: str | None,
    ) -> None:
        _read_only()

    def atualizar_inscricao(
        self,
        idinscricao: int,
        idprova: int,
        numeroprocesso: int,
        estado: str,
        indicador_da: bool,
        funcao: str | None,
    ) -> None:
        _read_only()

    def eliminar_inscricoes(self, ids: list[int]) -> None:
        _read_only()

    def criar_dorsal(
        self,
        inscricao_id: int,
        numero: int,
        estado: str,
        entregue_em: datetime | None,
    ) -> int:
        _read_only()

    def atualizar_dorsal(
        self,
        iddorsal: int,
        numero: int,
        estado: str,
        entregue_em: datetime | None,
    ) -> None:
        _read_only()

    def eliminar_dorsais(self, ids: list[int]) -> None:
        _read_only()

    def criar_chegada(
        self,
        inscricao_id: int,
        tempo_chegada: timedelta,
        metodo: str,
        corrigido_de: int | None,
    ) -> None:
        _read_only()

    def atualizar_chegada(
        self,
        idchegada: int,
        inscricao_id: int,
        tempo_chegada: timedelta,
        metodo: str,
        corrigido_de: int | None,
    ) -> None:
        _read_only()

    def eliminar_chegadas(self, ids: list[int]) -> None:
        _read_only()

    def criar_classificacao(
        self,
        inscricao_id: int,
        prova_id: int,
        escalao_id: int | None,
        posicao: int,
    ) -> None:
        _read_only()

    def atualizar_classificacao(
        self,
        idclassificacao: int,
        inscricao_id: int,
        prova_id: int,
        escalao_id: int | None,
        posicao: int,
    ) -> None:
        _read_only()

    def eliminar_classificacoes(self, ids: list[int]) -> None:
        _read_only()

    def criar_escalao(
        self,
        prova_id: int,
        designacao: str,
        sexo: str,
        anonasc_min: int,
        anonasc_max: int,
        da: bool,
    ) -> None:
        _read_only()

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
        _read_only()

    def eliminar_escalaoes(self, ids: list[int]) -> None:
        _read_only()

    def criar_regra_apuramento(
        self,
        prova_origem_id: int,
        prova_destino_id: int,
        escalao_id: int,
        numero_apurados: int,
    ) -> None:
        _read_only()

    def atualizar_regra_apuramento(
        self,
        idregra: int,
        prova_origem_id: int,
        prova_destino_id: int,
        escalao_id: int,
        numero_apurados: int,
    ) -> None:
        _read_only()

    def eliminar_regras_apuramento(self, ids: list[int]) -> None:
        _read_only()

    def gerar_apuramentos(self, prova_destino_id: int) -> int:
        _read_only()

    def atualizar_estado_apurado(
        self,
        inscricao_id: int,
        prova_destino_id: int,
        estado: str,
    ) -> None:
        _read_only()
