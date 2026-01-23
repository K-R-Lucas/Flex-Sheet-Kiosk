from flask import session
from web import config
import xlcalculator
import datetime
import openpyxl
import shutil
import os

class FlexSheet:
    def __init__(self, flexsheet_path: str):
        self.path = flexsheet_path
        self.temp = None
        self.load()
    
    def load(self):
        self.compiler = xlcalculator.ModelCompiler()
        self.data_book = xlcalculator.Evaluator(
            self.compiler.read_and_parse_archive(self.path)
        )
        self.book = openpyxl.load_workbook(self.path)

    @staticmethod
    def parse_date(datelike):
        if isinstance(datelike, float):
            return datetime.date.fromtimestamp((datelike - 25569)*86400)
    
        if isinstance(datelike, datetime.datetime):
            return datelike.date()
        
        if isinstance(datelike, datetime.date):
            return datelike

    def find_date(self, date: datetime.date, sheet_number: int = 1) -> tuple[any, int, int]:
        cells = [self.data_book.evaluate(f"Sheet {sheet_number} of 3!A{i}") for i in range(13, 33)]

        for row, cell in enumerate(cells):
            cell_date = self.parse_date(cell.value)
            cell.value = cell_date

            if cell_date == date:
                return (cell, row + 13, sheet_number)

        if sheet_number < 3:
            return self.find_date(date, sheet_number + 1)
        
        raise KeyError(f"Date {date} was not found...")

    def get_dates(self) -> list[datetime.date]:
        dates = list()

        for sheet_number in range(1, 4):
            for i in range(13, 33):
                cell = self.data_book.evaluate(f"Sheet {sheet_number} of 3!A{i}")
                date = self.parse_date(cell.value)

                dates.append(date)

        return dates

    def start_new_sheet(self, backup_dir: str, template_path: str):
        carried_hours = self.data_book.evaluate("Sheet 3 of 3!M40")
        carried_mins = self.data_book.evaluate("Sheet 3 of 3!N40")

        dates = self.get_dates()

        backup_path = os.path.join(
            backup_dir, f"{dates[0].isoformat()}_{dates[-1].isoformat()}.xlsx"
        )

        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        os.rename(self.path, backup_path)
        shutil.copy(template_path, self.path)

        new_book = openpyxl.load_workbook(self.path)
        sheet = new_book["Sheet 1 of 3"]
        sheet["B8"].value = datetime.datetime.combine(
            dates[-1] + datetime.timedelta(days=3), datetime.time()
        )
        sheet["K7"].value = carried_hours.value
        sheet["L7"].value = carried_mins.value
        new_book.save(self.path)

        self.load()

    @staticmethod
    def clamp_time(t: datetime.time, min_: float, max_: float):
        return min(max(min_, (t.hour + (t.minute + t.second/60)/60)/24), max_)
    
    def update_now(self):
        now = datetime.datetime.now()
        t = datetime.time(now.hour, now.minute)

        try:
            _, row, sheet_number = self.find_date(now.date())
        except KeyError:
            self.start_new_sheet(config.ARCHIVE_DIR, config.FLEX_TEMPLATE_PATH)
            _, row, sheet_number = self.find_date(now.date())

        sheet = self.book[f"Sheet {sheet_number} of 3"]

        for col in "BCD":
            cell_pos = f"{col}{row}"
            cell = sheet[cell_pos]

            if cell.value is None:
                match col:
                    case 'B':
                        cell.value = self.clamp_time(t, 7.5/24, 18/24)
                        break

                    case 'D':
                        cell.value = self.clamp_time(t, 7.5/24, 18/24)
                        break
                    
                    case 'C':
                        temp = session.get("break_start")

                        if temp is None:
                            session["break_start"] = now.isoformat()
                        
                        else:
                            before = datetime.datetime.fromisoformat(temp)
                            cell.value = min(max(int((now - before).seconds/60)/1440, 0.5/24), 3/24)
                            session.pop("break_start")
                        
                        session.modified = True
                        break

        self.book.save(self.path)
