import pandas as pd
import xlrd


def xlsx_reader(excel):
    """
    Helper function to get from xlsx to pandas df
    :param file: input file
    :return:
    """
    df = None
    try:
        sheets = pd.read_excel(excel, sheet_name=None, encoding='utf8')
        for name, sheet in sheets.items():
            sheet.columns = [c.lower() for c in sheet.columns]
            if 'address' in sheet.columns:
                df = sheet
    except xlrd.biffh.XLRDError:
        pass
    return df