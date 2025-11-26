import datetime
import locale

import pandas as pd
from fastapi import HTTPException

from app.dao.mysql import WorkTabelDAO, StructuralSubdivisionDAO
from app.models.postgres import User
from app.models.mysql.nitro import StructuralSubdivision as StructuralSubdivisionModel
from sqlalchemy.ext.asyncio import AsyncSession


class WorkTabelService:
    def __init__(self, session_nitro: AsyncSession):
        self.session_nitro = session_nitro

    async def work_tabel(self, year: int, month: int, current_user: User):
        data = await StructuralSubdivisionDAO(self.session_nitro).get_one_or_none(
            fields=[StructuralSubdivisionModel.id],
            filters={
                StructuralSubdivisionModel.dean: current_user.platonus_id,
            }
        )

        subdivision_id = data.id

        if not subdivision_id:
            raise HTTPException(status_code=404, detail="No subdivision found for this user")

        # === 1. Получаем данные ===
        dao = WorkTabelDAO(self.session_nitro)
        tutors_by_subdivision = await dao.get_tutors_by_subdivision(subdivision_id,  year, month)

        if not tutors_by_subdivision:
            raise HTTPException(status_code=404, detail="No tutors found for this subdivision")

        tutor_ids = list({row["TutorID"] for row in tutors_by_subdivision})

        dean_ids = list({row["dean"] for row in tutors_by_subdivision})

        if current_user.platonus_id not in dean_ids:
            raise HTTPException(status_code=403, detail="Access denied")

        hours_per_day = await dao.get_hours_sum_per_day(subdivision_id, tutor_ids, year, month)

        # === Маппинг типов ===
        fff = {
            '1000': "ІС",
            '2000': "ЕД",
            '3000': "ЭД",
            '4000': "ДД",
            '5000': "ЖС",
            '9000': "БЛ",
            '9999': "ПР",
        }

        # === Подмена часов на коды типа ===
        for row in hours_per_day:
            t = row.get("tabel_type")

            if t in fff:
                row["hour_sum"] = fff[t]

        # === 2. В DataFrame ===
        df_tutors = pd.DataFrame(tutors_by_subdivision)
        df_tabels = pd.DataFrame(hours_per_day)

        if df_tabels.empty:
            # Нет записей по табелю
            return []

        # === 3. Пивот по дням ===
        pivot = (
            df_tabels
            .pivot_table(
                index="tutor_id",
                columns="tabel_day",
                values="hour_sum",
                aggfunc="sum",
                fill_value=0
            )
            .reset_index()
        )

        # === 4. Объединяем с данными о преподавателях ===
        merged = pd.merge(
            pivot,
            df_tutors,
            left_on="tutor_id",
            right_on="TutorID",
            how="left"
        )

        # === 5. Формируем удобные колонки ===
        merged["fio"] = merged["lastname"] + " " + merged["firstname"] + " " + merged["patronymic"]

        # Все колонки-дни:
        day_columns = sorted([c for c in merged.columns if isinstance(c, int)])

        # === 6. Добавляем подсчёт рабочих дней ===
        merged["working_days"] = merged[day_columns].apply(lambda row: sum(self.is_working(v) for v in row), axis=1)
        merged["unworking_days"] = merged[day_columns].apply(
            lambda row: sum(not bool(self.is_working(v)) for v in row),
            axis=1
        )

        # === 7. Собираем результат ===
        day_columns = sorted([c for c in merged.columns if isinstance(c, int)])

        # Добавляем столбец hours_per_day (словарь по дням)
        merged["hours_per_day"] = merged[day_columns].apply(lambda row: {str(day): row[day] for day in day_columns},
                                                            axis=1)
        # Формируем итоговый DataFrame (без отдельных дневных колонок)
        result = merged[["fio", "position_name", "hours_per_day", "working_days", "unworking_days"]]

        # === 8. Возвращаем JSON ===
        return result.to_dict(orient="records")

    async def generate_table_html(self, year, month, staff_data):
        html_content = """
        <table border="1">
            <tbody><tr><td colspan="36"><b>Кадрлардың біліктілігін арттыру және қайта даярлау институты<br>Жұмыс уақытын есепке алу табелі</b></td></tr>
                <tr><td colspan="36"><b>2025 жылдың қараша айына</b></td></tr>
                <tr><td colspan="36"><b></b></td></tr>

            <tr>
                <th>#</th>
                <th>Фамилия Аты Әкесінің аты</th>
                <th>Қызмет атауы</th>
        """

        for day in range(1, 31):
            html_content += f'<th>{day}<br>{self.get_weekday(year, month, day)}</th>'

        html_content += """
                    <th>ЖК</th>
                <th>ЖЖК</th>
                <th>Ескерту</th>
            </tr>
        """

        managers = [p for p in staff_data if p["position_name"].strip().lower() == "басшы"]
        other_staff = [p for p in staff_data if p["position_name"].strip().lower() != "басшы"]

        if managers:
            html_content += '<tr><td colspan="36"><b>Бөлімше&nbsp;басшысы</b></td></tr>'

            for i, person in enumerate(managers):
                html_content += self.generate_person_row(year, month, person, i + 1)

        html_content += '<tr><td colspan="36"><b>Негізгі жүктеме</b></td></tr>'

        for i, person in enumerate(other_staff):
            html_content += self.generate_person_row(year, month, person, i + 1)

        html_content += """
            <tr><td colspan="36"><hr><b>Шартты белгілер:</b><br>Іссапар - ІС<br>Декреттік демалыс - ДД<br>Экологиялық демалыс - ЭД<br>Еңбек демалысы - ЕД<br>Жалақысы сақталмайтын&nbsp;демалыс&nbsp;-&nbsp;ЖС</td></tr>
        </tbody>
            </table>
        """

        return html_content

    def generate_person_row(self, year, month, person, row_number):
        fio = person["fio"]
        position = person["position_name"]
        hours_per_day = person["hours_per_day"]
        working_days = person.get("working_days", 0)  # ЖК
        unworking_days = person.get("unworking_days", 0)  # ЖЖК

        row_html = f"""
        <tr>
            <td>{row_number}</td>
            <td>{fio}</td>
            <td>{position}</td>
        """

        # Предположим, что все дни, для которых нет данных, являются выходными 'В' или прочерками '-'
        # Если час равен 0.0, то это выходной (В). Если есть значение, то его отображаем.

        for day in range(1, 31):
            day_str = str(day)
            hour_value = hours_per_day.get(day_str, 0.0)  # По умолчанию 0.0, если нет данных

            if self.is_weekend(year, month, day):
                if hour_value == 0.0:
                    display_value = "В"
                else:
                    display_value = str(hour_value)  # Если работали в выходной
            else:  # Рабочий день
                if hour_value == 0.0:
                    display_value = "-"
                else:
                    display_value = str(hour_value)

            row_html += f'<td>{display_value}</td>'

        row_html += f"""
                <td>{working_days}</td>
                <td>{unworking_days}</td>
                <td></td>
            </tr>
        """

        return row_html

    @staticmethod
    def get_weekday(year: int, month: int, day: int) -> str:
        locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
        date = datetime.date(year, month, day)

        return date.strftime("%a").upper()

    @staticmethod
    def is_weekend(year: int, month: int, day: int) -> bool:
        weekday = datetime.date(year, month, day).weekday()

        return weekday >= 5

    @staticmethod
    def is_working(value):
        # return isinstance(value, (int, float))
        if isinstance(value, (int, float)):
            return value > 0

        # if isinstance(value, str) and value.strip() != "":
        #     return True
        return False
