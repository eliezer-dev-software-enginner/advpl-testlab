import shutil
import unicodedata
from decimal import Decimal


class PreviewComplete(Exception):
    pass


def text(value):
    return ''.join(char if not unicodedata.category(char).startswith('C') else ' '
                   for char in str(value))


def format_cell(value, metadata):
    if value is None:
        return ''
    if metadata.get('tipo', '').upper() == 'D':
        if hasattr(value, 'ordinal'):
            return value.value.strftime('%d/%m/%Y') if value.ordinal else ''
        from datetime import date
        if value:
            try:
                return date.fromisoformat(str(value)).strftime('%d/%m/%Y')
            except ValueError:
                pass
    if metadata.get('tipo', '').upper() == 'N' and isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        decimals = metadata.get('decimais', 0)
        decimals = decimals if isinstance(decimals, int) and 0 <= decimals <= 10 else 0
        return f'{value:,.{decimals}f}'.translate(str.maketrans(',.', '.,'))
    return text(value)


def render_browse(title, alias, columns, rows, actions, legends=(), width=None, total=None):
    width = max(40, width or shutil.get_terminal_size((120, 24)).columns)
    total = len(rows) if total is None else total
    print('=' * width)
    print(f'PREVIEW DO BROWSE | {text(title)}')
    print(f'Alias: {text(alias)} | {total} registro(s) no mock')
    print('Acoes: ' + (' '.join(f'[{text(action)}]' for action in actions) or '(nenhuma definida)'))
    print('Simulacao local; acoes nao sao executadas. Nao representa a interface grafica exata.')
    print('-' * width)
    widths = [min(28, max(3, len(text(column)), *(len(text(row[i])) for row in rows)))
              for i, column in enumerate(columns)]
    groups = []
    group = []
    for index, size in enumerate(widths):
        if group and sum(widths[i] + 3 for i in group) + size + 4 > width:
            groups.append(group)
            group = []
        group.append(index)
    if group:
        groups.append(group)
    for group_index, group in enumerate(groups, 1):
        if len(groups) > 1:
            print(f'Colunas {group_index}/{len(groups)} (mesmos registros)')
        def line(values):
            cells = []
            for i in group:
                value = text(values[i])
                if len(value) > widths[i]:
                    value = value[:widths[i] - 3] + '...'
                cells.append(value.ljust(widths[i]))
            return '| ' + ' | '.join(cells) + ' |'
        print(line(columns))
        print('+-' + '-+-'.join('-' * widths[i] for i in group) + '-+')
        for row in rows:
            print(line(row))
        print()
    if not columns:
        print('Sem colunas: declare campos no mock ou use AddColumn/SetFields no fonte.')
    if not rows:
        print('Nenhum registro encontrado no mock.')
    if total > len(rows):
        print(f'Mostrando os primeiros {len(rows)} de {total} registros.')
    labels = [text(legend[2]) for legend in legends if len(legend) >= 3]
    if labels:
        print('Legendas: ' + ' | '.join(labels))
    print('=' * width)
