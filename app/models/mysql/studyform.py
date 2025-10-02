from typing import Optional
import datetime
import decimal

from sqlalchemy import Double, ForeignKeyConstraint, Index, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.mysql_connection import MySQLBase


class BaseEducation(MySQLBase):
    __tablename__ = 'base_education'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    namekz: Mapped[Optional[str]] = mapped_column(String(64))
    nameru: Mapped[Optional[str]] = mapped_column(String(64))
    nameen: Mapped[Optional[str]] = mapped_column(String(64))

    studyforms: Mapped[list['Studyform']] = relationship('Studyform', back_populates='base_education')



class Studyform(MySQLBase):
    __tablename__ = 'studyforms'
    __table_args__ = (
        ForeignKeyConstraint(['base_education_id'], ['base_education.id'], name='studyform_baseEducation'),
        Index('IX_studyforms_degreeID', 'degreeID'),
        Index('studyform_baseEducation', 'base_education_id')
    )

    Id: Mapped[int] = mapped_column(Integer, primary_key=True)
    modified: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    degreeID: Mapped[Optional[int]] = mapped_column(Integer)
    NameRu: Mapped[Optional[str]] = mapped_column(String(128))
    NameKz: Mapped[Optional[str]] = mapped_column(String(128))
    NameEn: Mapped[Optional[str]] = mapped_column(String(128))
    formschedule: Mapped[Optional[int]] = mapped_column(TINYINT(1))
    courseCount: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    maxYearsCount: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    creditsCount: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    checksCount: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    enaughGraduateGPA: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True), server_default=text("'0'"))
    excellentGraduateGPA: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True), server_default=text("'0'"))
    finalAttEnaughCredits: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    termsCount: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    editIUPDaysCount: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'2'"))
    departmentID: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'1'"))
    current_part: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True))
    ratings_part: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True))
    exam_part: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True))
    use_ratings: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    count_all_ratings: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    excDiplomaNoRetake: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))
    excDiplomaNoSatisfactoryMark: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))
    excDiplomaGosProjectExcellentMarks: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))
    term_credits: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True))
    summer_term_credits: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True))
    change_percent: Mapped[Optional[int]] = mapped_column(Integer)
    average_weekly_load_hours: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    base_education_id: Mapped[Optional[int]] = mapped_column(Integer)
    allow_with_nopass: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    standard_study_education_month: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    standard_study_education_year: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    percentage_excellent: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    onlineRegProvided: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    diploma_honor_provided: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    block_journal: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    is_sufficient_gpa_for_course: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))
    is_transcript_unsatisfactory_marks_absent: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    is_overall_average_gpa_sufficient: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    overall_average_gpa: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True), server_default=text("'0'"))
    is_assimilated_credits_sufficient: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    official_duration_of_the_program_ru: Mapped[Optional[str]] = mapped_column(String(256), server_default=text("''"))
    official_duration_of_the_program_kz: Mapped[Optional[str]] = mapped_column(String(256), server_default=text("''"))
    official_duration_of_the_program_en: Mapped[Optional[str]] = mapped_column(String(256), server_default=text("''"))
    trainingCompletionTerm: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'2'"))
    termOfSubjectsInEuropeanDiploma: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'-1'"))
    distance_learning: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"), comment='Форма для дистанционного обучения')
    exc_diploma_take_into_account_theoretical_gos_disciplines: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"), comment='Учитывать дисциплины с формой контроля государственный экзамен, по которым предусмотрено теоретическое обучение')
    payment_debts: Mapped[Optional[str]] = mapped_column(String(128), comment='Причина задолженности')
    providedRemoveControls: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"), comment='Предусмотреть удаление рубежного контроля')
    f7219: Mapped[Optional[str]] = mapped_column(String(255))
    f7218: Mapped[Optional[str]] = mapped_column(String(2))
    f5568: Mapped[Optional[str]] = mapped_column(String(2))
    onamekz: Mapped[Optional[str]] = mapped_column(String(512))
    onameru: Mapped[Optional[str]] = mapped_column(String(255))
    onameen: Mapped[Optional[str]] = mapped_column(String(255))
    onamerus: Mapped[Optional[str]] = mapped_column(String(255))
    retake_types: Mapped[Optional[str]] = mapped_column(String(64), server_default=text("'1'"), comment='Какие виды пересдач по итоговому контролю не должны быть для выдачи диплома с отличием')
    markTypes: Mapped[Optional[str]] = mapped_column(String(128), comment='Типы оценок')
    in_use: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"), comment='Используется')
    completion_month_main_admission: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'6'"), comment='Месяц завершения программы обучения для основного приема')
    completion_month_winter_admission: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'6'"), comment='Месяц завершения программы обучения для зимнего приема')

    base_education: Mapped[Optional['BaseEducation']] = relationship('BaseEducation', back_populates='studyforms')
