from sqladmin import ModelView

from datetime import datetime

from app.models.postgres.user import User
from app.models.postgres.user_info import UserInfo
from app.models.postgres.role import Role
from app.models.postgres.user_role import UserRole
from app.models.postgres.document import Document
from app.models.postgres.document_type import DocumentType
from app.models.postgres.document_type_group import DocumentTypeGroup
from app.models.postgres.approver import Approver
from app.models.postgres.role_document_type_group import RoleDocumentTypeGroup



def custom_datetime_formatter(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else None


class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"

    column_list = [
        User.id,
        User.platonus_id,
        User.is_student,
        User.bin_number,
        User.user_roles,
        User.created_at,
        User.updated_at
    ]

    column_searchable_list = [
        User.platonus_id,
        User.bin_number
    ]

    column_sortable_list = [
        User.id,
        User.platonus_id,
        User.is_student,
        User.created_at,
        User.updated_at
    ]

    column_type_formatters = {
        datetime: custom_datetime_formatter
    }

    form_columns = [
        User.platonus_id,
        User.is_student,
        User.bin_number
    ]


class UserRoleAdmin(ModelView, model=UserRole):
    name = "Роль пользователя"
    name_plural = "Роли пользователей"

    column_list = [
        UserRole.user,
        UserRole.role,
        UserRole.created_at,
        UserRole.updated_at
    ]

    column_searchable_list = [
        "user.platonus_id",
        "role.name_ru"
    ]

    column_sortable_list = [
        UserRole.created_at,
        UserRole.updated_at
    ]

    form_columns = [
        "user",
        "role"
    ]


class DocumentAdmin(ModelView, model=Document):
    name = "Документ"
    name_plural = "Документы"

    column_list = [
        Document.id,
        Document.name,
        Document.author_user,
        Document.recipient_user,
        Document.document_type,
        Document.sigex_id,
        Document.status,
        Document.status_updated_at,
        Document.created_at,
        Document.updated_at
    ]

    column_searchable_list = [
        "id",
        "name",
        "document_type.name_ru",
        "sigex_id",
    ]

    column_sortable_list = [
        Document.id,
        Document.name,
        Document.author_user,
        Document.recipient_user,
        Document.document_type,
        Document.sigex_id,
        Document.status,
        Document.status_updated_at,
        Document.created_at,
        Document.updated_at
    ]

    column_type_formatters = {
        datetime: custom_datetime_formatter
    }


class DocumentTypeGroupAdmin(ModelView, model=DocumentTypeGroup):
    name = "Группа документов"
    name_plural = "Группы документов"

    column_list = [
        DocumentTypeGroup.id,
        DocumentTypeGroup.name_ru,
        DocumentTypeGroup.name_kz,
        DocumentTypeGroup.is_active,
        DocumentTypeGroup.created_at,
        DocumentTypeGroup.updated_at
    ]

    column_searchable_list = [
        DocumentTypeGroup.name_ru,
        DocumentTypeGroup.name_kz
    ]

    column_sortable_list = [
        DocumentTypeGroup.id,
        DocumentTypeGroup.name_ru,
        DocumentTypeGroup.name_kz,
        DocumentTypeGroup.is_active,
        DocumentTypeGroup.created_at,
        DocumentTypeGroup.updated_at
    ]

    column_type_formatters = {
        datetime: custom_datetime_formatter
    }


class DocumentTypeAdmin(ModelView, model=DocumentType):
    name = "Тип документа"
    name_plural = "Типы документов"

    column_list = [
        DocumentType.id,
        DocumentType.document_type_group,
        DocumentType.name_ru,
        DocumentType.name_kz,
        DocumentType.is_active,
        DocumentType.created_at,
        DocumentType.updated_at
    ]

    column_searchable_list = [
        DocumentType.name_ru,
        DocumentType.name_kz
    ]

    column_sortable_list = [
        DocumentType.id,
        DocumentType.name_ru,
        DocumentType.name_kz,
        DocumentType.is_active,
        DocumentType.created_at,
        DocumentType.updated_at
    ]

    column_type_formatters = {
        datetime: custom_datetime_formatter
    }


class UserInfoAdmin(ModelView, model=UserInfo):
    name = "Информация о пользователе"
    name_plural = "Информация о пользователях"

    column_list = [
        UserInfo.user,
        UserInfo.lastname,
        UserInfo.firstname,
        UserInfo.patronymic,
        UserInfo.iin_number,
        UserInfo.created_at,
        UserInfo.updated_at
    ]

    column_searchable_list = [
        UserInfo.lastname,
        UserInfo.firstname,
        UserInfo.patronymic,
        UserInfo.iin_number
    ]

    column_sortable_list = [
        UserInfo.lastname,
        UserInfo.firstname,
        UserInfo.patronymic,
        UserInfo.iin_number,
        UserInfo.created_at,
        UserInfo.updated_at
    ]

    column_type_formatters = {
        datetime: custom_datetime_formatter
    }


class RoleAdmin(ModelView, model=Role):
    name = "Роль"
    name_plural = "Роли"

    column_list = [
        Role.id,
        Role.name_ru,
        Role.name_kz,
        Role.is_active,
        Role.created_at,
        Role.updated_at
    ]

    form_excluded_columns = [
        "users",
        "user_roles",
        "created_at",
        "updated_at",
        "document_type_groups"
    ]

    column_searchable_list = [
        Role.name_ru,
        Role.name_kz
    ]

    column_sortable_list = [
        Role.id,
        Role.name_ru,
        Role.name_kz,
        Role.is_active,
        Role.created_at,
        Role.updated_at
    ]

    column_type_formatters = {
        datetime: custom_datetime_formatter
    }


class ApproverAdmin(ModelView, model=Approver):
    name = "Согласующий"
    name_plural = "Согласующие"

    column_list = [
        Approver.approver_user,
        Approver.document,
        Approver.status,
        Approver.is_recipient,
        Approver.status_updated_at,
        Approver.created_at,
        Approver.updated_at
    ]

    column_searchable_list = [
        Approver.approver_user,
        Approver.document
    ]

    column_sortable_list = [
        Approver.approver_user,
        Approver.document,
        Approver.status,
        Approver.is_recipient,
        Approver.status_updated_at,
        Approver.created_at,
        Approver.updated_at
    ]

    column_type_formatters = {
        datetime: custom_datetime_formatter
    }


class RoleDocumentTypeGroupAdmin(ModelView, model=RoleDocumentTypeGroup):
    name = "Доступ роли к группе документов"
    name_plural = "Доступы ролей к группам документов"

    column_list = [
        RoleDocumentTypeGroup.role,
        RoleDocumentTypeGroup.group
    ]

    form_excluded_columns = [
        "created_at",
        "updated_at"
    ]

    column_searchable_list = [
        RoleDocumentTypeGroup.role,
        RoleDocumentTypeGroup.group
    ]

    column_sortable_list = [
        RoleDocumentTypeGroup.role,
        RoleDocumentTypeGroup.group
    ]

    column_type_formatters = {
        datetime: custom_datetime_formatter
    }
