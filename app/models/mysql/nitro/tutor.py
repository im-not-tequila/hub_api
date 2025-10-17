from typing import Optional
import datetime
import decimal

from sqlalchemy import BigInteger, Date, Double, Index, Integer, SmallInteger, String, TIMESTAMP, Text, text
from sqlalchemy.dialects.mysql import MEDIUMBLOB, MEDIUMTEXT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.mysql_connection import NitroBase


class Tutor(NitroBase):
    __tablename__ = 'tutors'
    __table_args__ = (
        Index('IDX_tutors_miletarystatus', 'militarystatus'),
        Index('IDX_tutors_nobdid', 'percofaceid'),
        Index('IDX_tutors_subdivisionid', 'subdivisionid'),
        Index('del', 'del'),
        Index('deleted', 'deleted'),
        Index('firstname', 'firstname'),
        Index('icFinishDate', 'icFinishDate'),
        Index('idx_academicStatusID', 'AcademicStatusID'),
        Index('idx_job_title_int', 'job_title_int'),
        Index('lastname', 'lastname'),
        Index('nat', 'nat'),
        Index('patronymic', 'patronymic'),
        Index('percoid', 'percoid'),
        Index('sit', 'sit'),
        Index('tablelnumber', 'tablelnumber'),
        Index('telegramid', 'telegramid')
    )

    TutorID: Mapped[int] = mapped_column(Integer, primary_key=True)
    update_date: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False,
                                                           server_default=text('CURRENT_TIMESTAMP'))
    sovmestid: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("'0'"))
    telegramid: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("'0'"))
    del_: Mapped[int] = mapped_column('del', TINYINT, nullable=False, server_default=text("'0'"))
    bornInAnotherCountry: Mapped[int] = mapped_column(TINYINT(1), nullable=False, server_default=text("'0'"))
    otherBornCountryID: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("'0'"))
    percoid: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'0'"))
    subdivisionid: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("'0'"))
    firstname: Mapped[Optional[str]] = mapped_column(String(128))
    lastname: Mapped[Optional[str]] = mapped_column(String(128))
    patronymic: Mapped[Optional[str]] = mapped_column(String(128))
    BirthDate: Mapped[Optional[datetime.date]] = mapped_column(Date)
    StartDate: Mapped[Optional[datetime.date]] = mapped_column(Date)
    work_start_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    FinishDate: Mapped[Optional[datetime.date]] = mapped_column(Date)
    Login: Mapped[Optional[str]] = mapped_column(String(128))
    Password: Mapped[Optional[str]] = mapped_column(String(128))
    phone: Mapped[Optional[str]] = mapped_column(String(256))
    adress: Mapped[Optional[str]] = mapped_column(String(512))
    mail: Mapped[Optional[str]] = mapped_column(String(512))
    has_access: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))
    SexID: Mapped[Optional[int]] = mapped_column(Integer)
    NationID: Mapped[Optional[int]] = mapped_column(Integer)
    photo: Mapped[Optional[bytes]] = mapped_column(MEDIUMBLOB)
    rnn: Mapped[Optional[str]] = mapped_column(String(32))
    sikplt: Mapped[Optional[str]] = mapped_column(String(32))
    iinplt: Mapped[Optional[str]] = mapped_column(String(32))
    rang: Mapped[Optional[str]] = mapped_column(MEDIUMTEXT)
    ScientificDegreeID: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'1'"))
    AcademicStatusID: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'1'"))
    edubase: Mapped[Optional[str]] = mapped_column(Text)
    RATE: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True))
    RoleID: Mapped[Optional[int]] = mapped_column(Integer)
    CafedraID: Mapped[Optional[int]] = mapped_column(Integer)
    deleted: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    icnumber: Mapped[Optional[str]] = mapped_column(String(256))
    icdate: Mapped[Optional[datetime.date]] = mapped_column(Date)
    icFinishDate: Mapped[Optional[datetime.date]] = mapped_column(Date)
    icdepartment: Mapped[Optional[str]] = mapped_column(String(256))
    ismarried: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    job_title: Mapped[Optional[str]] = mapped_column(String(256))
    ftutor: Mapped[Optional[int]] = mapped_column(TINYINT(1))
    funiversity: Mapped[Optional[str]] = mapped_column(Text)
    ftitle: Mapped[Optional[str]] = mapped_column(Text)
    fdates: Mapped[Optional[str]] = mapped_column(Text)
    timetable_description: Mapped[Optional[str]] = mapped_column(Text)
    teaching_experience_start_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    is_clerk: Mapped[Optional[int]] = mapped_column(TINYINT(1))
    fcountryID: Mapped[Optional[int]] = mapped_column(Integer)
    funiversityID: Mapped[Optional[int]] = mapped_column(Integer)
    fuPlaceWorldRankings: Mapped[Optional[int]] = mapped_column(Integer)
    fnumberHoursRK: Mapped[Optional[int]] = mapped_column(Integer)
    fnumberHoursECTS: Mapped[Optional[int]] = mapped_column(Integer)
    fsourceOfFinance: Mapped[Optional[int]] = mapped_column(Integer)
    fOfAllCosts: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True))
    ScientificFieldID: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'1'"))
    registration_place: Mapped[Optional[str]] = mapped_column(String(512))
    living_place: Mapped[Optional[str]] = mapped_column(String(512))
    living_adress: Mapped[Optional[str]] = mapped_column(String(512))
    work_status: Mapped[Optional[int]] = mapped_column(Integer)
    job_title_int: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    blocked: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    updated: Mapped[Optional[str]] = mapped_column(String(16), server_default=text("'same'"))
    maternity_leave: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    on_foreign_trip: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    passwordLdap: Mapped[Optional[str]] = mapped_column(String(128))
    firstname_ru: Mapped[Optional[str]] = mapped_column(String(128))
    lastname_ru: Mapped[Optional[str]] = mapped_column(String(128))
    patronymic_ru: Mapped[Optional[str]] = mapped_column(String(128))
    firstname_en: Mapped[Optional[str]] = mapped_column(String(128))
    lastname_en: Mapped[Optional[str]] = mapped_column(String(128))
    patronymic_en: Mapped[Optional[str]] = mapped_column(String(128))
    lastnamePrevious: Mapped[Optional[str]] = mapped_column(String(128))
    isTemporaryPassword: Mapped[Optional[int]] = mapped_column(TINYINT(1))
    mobilePhone: Mapped[Optional[str]] = mapped_column(String(128))
    ictype: Mapped[Optional[int]] = mapped_column(Integer)
    icseries: Mapped[Optional[str]] = mapped_column(String(256))
    departmentid: Mapped[Optional[int]] = mapped_column(Integer)
    citizenshipID: Mapped[Optional[int]] = mapped_column(Integer)
    additionalInformation: Mapped[Optional[str]] = mapped_column(String(256))
    centaurus_theme_id: Mapped[Optional[str]] = mapped_column(String(256))
    auth_key: Mapped[Optional[str]] = mapped_column(String(32), comment='ayan2018')
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), comment='ayan2018')
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255), comment='ayan2018')
    emailConfirm: Mapped[Optional[int]] = mapped_column(SmallInteger, server_default=text("'20'"), comment='ayan2018')
    email_confirm_token: Mapped[Optional[str]] = mapped_column(String(255), comment='ayan2018')
    created_at: Mapped[Optional[int]] = mapped_column(Integer, comment='ayan2018')
    updated_at: Mapped[Optional[int]] = mapped_column(Integer, comment='ayan2018')
    passwordLdapSSHA: Mapped[Optional[str]] = mapped_column(String(256))
    icdepartmentID: Mapped[Optional[int]] = mapped_column(Integer)
    vuchet_vus: Mapped[Optional[str]] = mapped_column(String(255))
    vuchet_doctype: Mapped[Optional[int]] = mapped_column(TINYINT)
    vuchet_docnumber: Mapped[Optional[str]] = mapped_column(String(25))
    vuchet_zvan: Mapped[Optional[str]] = mapped_column(String(25))
    vuchet_godnost: Mapped[Optional[int]] = mapped_column(TINYINT)
    passwordLdapAd: Mapped[Optional[str]] = mapped_column(String(256), comment='Active directory')
    flanguage_skill_lang: Mapped[Optional[int]] = mapped_column(Integer, comment='владения иностранным языком')
    flanguage_skill_level: Mapped[Optional[int]] = mapped_column(Integer, comment='Уровень владения по ОЕК')
    ic_finish_date: Mapped[Optional[datetime.date]] = mapped_column(Date,
                                                                    comment='Срок действия документа, удостоверяющего личность')
    incorrectIin: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"), comment='Неверный ИИН')
    assignedIinIssuedByPublicBody: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"),
                                                                         comment='Заданный ИИН выдан государственным органом')
    tablelnumber: Mapped[Optional[str]] = mapped_column(String(9), server_default=text("'000000000'"))
    birthplace: Mapped[Optional[str]] = mapped_column(String(512))
    other_birth_place: Mapped[Optional[str]] = mapped_column(String(512))
    timetable_description_kz: Mapped[Optional[str]] = mapped_column(Text)
    timetable_description_en: Mapped[Optional[str]] = mapped_column(Text)
    birthcountry: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'113'"))
    birthplacecode: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'113'"))
    invalid: Mapped[Optional[int]] = mapped_column(TINYINT, server_default=text("'0'"))
    militarystatus: Mapped[Optional[int]] = mapped_column(TINYINT, server_default=text("'0'"))
    percofaceid: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    nat: Mapped[Optional[int]] = mapped_column(Integer)
    sit: Mapped[Optional[int]] = mapped_column(Integer)
    du: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    birth_place_cato_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Населенный пункт рождения (като)')
    contractTypeId: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'1'"))
    registration_place_cato_id: Mapped[Optional[int]] = mapped_column(Integer,
                                                                      comment='Населенный пункт прописки (като)')
    living_place_cato_id: Mapped[Optional[int]] = mapped_column(Integer, comment='Населенный пункт проживания (като)')
    categoryid: Mapped[Optional[int]] = mapped_column(Integer)
    hasCriminalRecord: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    hasMedicalRecord: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    is_hired_instead: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    replaced_tutor_id: Mapped[Optional[int]] = mapped_column(Integer)
    educationOrderNumber: Mapped[Optional[str]] = mapped_column(String(256),
                                                                comment='номер приказа в подразделении - сведения об образовании')
    educationOrderDate: Mapped[Optional[datetime.date]] = mapped_column(Date,
                                                                        comment='дата приказа в подразделении - сведения об образовании')
    bankRequisites: Mapped[Optional[str]] = mapped_column(String(64), comment='Банковские реквизиты')
    provided_with_housing: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    room_count: Mapped[Optional[int]] = mapped_column(Integer)
    inhabitants_count: Mapped[Optional[int]] = mapped_column(Integer)
    period_of_staying_start_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    period_of_staying_end_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    viceRector: Mapped[Optional[str]] = mapped_column(String(1))
    liveRegType: Mapped[Optional[int]] = mapped_column(Integer, comment='Тип регистрации проживания')
    livingPeriodStart: Mapped[Optional[datetime.date]] = mapped_column(Date,
                                                                       comment='Уведомление о прибытии иностранного гражданина - Период пребывания старт')
    livingPeriodEnd: Mapped[Optional[datetime.date]] = mapped_column(Date,
                                                                     comment='Уведомление о прибытии иностранного гражданина - Период пребывания конец')
    allowanceNumber: Mapped[Optional[str]] = mapped_column(String(256),
                                                           comment='Разрешение на временное проживание - Номер разрешения')
    allowanceDateStart: Mapped[Optional[datetime.date]] = mapped_column(Date,
                                                                        comment='Разрешение на временное проживание - Дата начала разрешения')
    allowanceDateEnd: Mapped[Optional[datetime.date]] = mapped_column(Date,
                                                                      comment='Разрешение на временное проживание - Дата окончания разрешения')
    employee_type: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"),
                                                         comment='Тип сотрудника. «Сотрудник» (по умолчанию) или «Научный консультант»')
    scientific_consultant_type: Mapped[Optional[int]] = mapped_column(Integer,
                                                                      comment='Тип научного консультанта если сотрудник является Научный консультантом по полю employee_type')
    by_agreement: Mapped[Optional[int]] = mapped_column(TINYINT(1), comment='По договору')
    contract_start_date: Mapped[Optional[datetime.date]] = mapped_column(Date, comment='Срок действия договора c')
    contract_finish_date: Mapped[Optional[datetime.date]] = mapped_column(Date, comment='Срок действия договора по')
    main_place_of_work: Mapped[Optional[int]] = mapped_column(Integer, comment='Основное место работы')
    country_of_arrival: Mapped[Optional[int]] = mapped_column(Integer, comment='Страна прибытия')
    name_of_hpeo: Mapped[Optional[str]] = mapped_column(String(256), comment='Наименование ОВПО')
    source_of_finance: Mapped[Optional[int]] = mapped_column(Integer, comment='Источник финансирования')
    master_class_made_hours: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"),
                                                                   comment='Количество проведенных мастер-классов, часы')
    trainings_made_hours: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"),
                                                                comment='Количество проведенных мастер-классов, часы')
    was_speaker_on_conferences: Mapped[Optional[int]] = mapped_column(Integer,
                                                                      comment='Участие в качестве спикера на различных круглых столах, конференциях и встречах')
    developed_working_programs: Mapped[Optional[int]] = mapped_column(Integer,
                                                                      comment='Разработка рабочих программ дисциплин и сопровождающих учебно-методических материалов')
    format_of_work: Mapped[Optional[int]] = mapped_column(Integer, comment='Формат')
    workplace_orgname_ru: Mapped[Optional[str]] = mapped_column(Text,
                                                                comment='Наименование основного места работы на русском языке')
    workplace_orgname_kz: Mapped[Optional[str]] = mapped_column(Text,
                                                                comment='Наименование основного места работы на казахском языке')
    workplace_orgname_en: Mapped[Optional[str]] = mapped_column(Text,
                                                                comment='Наименование основного места работы на английском языке')
    lectures_made_hours: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"),
                                                               comment='Количество проведенных лекций, часы')
    seminars_made_hours: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"),
                                                               comment='Количество проведенных семинаров, часы')
    scopusID: Mapped[Optional[str]] = mapped_column(String(256))
    webOfScienceID: Mapped[Optional[str]] = mapped_column(String(256))
    mobile_phone_code: Mapped[Optional[str]] = mapped_column(Text)
    remove_from_the_list_epvo: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    attractedTutorId: Mapped[Optional[int]] = mapped_column(Integer, comment='Привлёк в ОВПО преподаватель')
    attractedYear: Mapped[Optional[int]] = mapped_column(Integer, comment='Привлёк в ОВПО преподаватель')

    tutor_cafedra: Mapped[list['TutorCafedra']] = relationship('TutorCafedra', back_populates='tutors')
