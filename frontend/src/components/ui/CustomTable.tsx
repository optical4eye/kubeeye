import React from 'react';
import { Table, TableProps } from 'antd';

interface CustomTableProps<T> extends TableProps<T> {
  variant?: 'default' | 'bordered' | 'striped';
}

const CustomTable = <T extends object>({ variant = 'default', ...props }: CustomTableProps<T>) => {
  const getTableProps = (): TableProps<T> => {
    const baseProps: TableProps<T> = {
      ...props,
      size: 'middle',
      pagination: {
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total, range) => `${range[0]}-${range[1]} из ${total}`,
        ...props.pagination,
      },
    };

    if (variant === 'bordered') {
      baseProps.bordered = true;
    }

    if (variant === 'striped') {
      baseProps.rowClassName = (record, index) =>
        index % 2 === 0 ? 'table-row-even' : 'table-row-odd';
    }

    return baseProps;
  };

  return <Table {...getTableProps()} />;
};

export default CustomTable;
