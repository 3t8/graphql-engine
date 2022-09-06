import { CockroachDBTable } from '..';
import { runSQL } from '../../api';
import { adaptTableColumns } from '../../common/utils';
import { GetTableColumnsProps } from '../../types';

export const getTableColumns = async ({
  dataSourceName,
  table,
  httpClient,
}: GetTableColumnsProps) => {
  const { name, schema } = table as CockroachDBTable;

  const sql = `
  SELECT 
   column_name, data_type 
  FROM 
    information_schema.columns 
  WHERE 
    table_schema = '${name}' AND 
    table_name  = '${schema}';`;

  const tables = await runSQL({
    source: {
      name: dataSourceName,
      kind: 'cockroach',
    },
    sql,
    httpClient,
  });

  return adaptTableColumns(tables.result);
};
