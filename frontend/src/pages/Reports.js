import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Select, Input, Space, Tag, Modal, Descriptions, Alert, Statistic, Row, Col, Tabs, Collapse, Tooltip } from 'antd';
import { DownloadOutlined, DeleteOutlined, EyeOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { getReports, getReport, deleteReport, exportReport, getCleanupConfig } from '../services/api';

const { Option } = Select;
const { Search } = Input;

const getInspectionItems = (reportDetail) => {
  if (!reportDetail) return [];

  // Handle new data structure with inspection_results
  if (reportDetail.inspection_results) {
    const allItems = [];
    Object.values(reportDetail.inspection_results).forEach(inspectorResult => {
      if (inspectorResult.items) {
        allItems.push(...inspectorResult.items);
      }
    });
    return allItems;
  }

  // Handle old data structure with direct items field
  return reportDetail.items || [];
};

const InspectionDetails = ({ items }) => {
  const getStatusTag = (status) => {
    switch (status) {
      case 'passed':
      case 'success':
        return <Tag color="#50fa7b">Успешно</Tag>;
      case 'exception':
        return <Tag color="#ff5555">Ошибка</Tag>;
      case 'failed':
        return <Tag color="#ff5555">Неудачно</Tag>;
      case 'warning':
        return <Tag color="#f1fa8c">Предупреждение</Tag>;
      default:
        return <Tag color="#bd93f9">Неизвестно</Tag>;
    }
  };

  const getSeverityTag = (severity) => {
    switch (severity) {
      case 'critical':
        return <Tag color="#ff5555">Критично</Tag>;
      case 'warning':
        return <Tag color="#f1fa8c">Предупреждение</Tag>;
      case 'info':
        return <Tag color="#bd93f9">Информация</Tag>;
      default:
        return <Tag color="#6272a4">Неизвестно</Tag>;
    }
  };

  const columns = [
    {
      title: 'Название проверки',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (status) => getStatusTag(status),
    },
    {
      title: 'Уровень серьезности',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity) => getSeverityTag(severity),
    },
    {
      title: 'Описание',
      dataIndex: 'description',
      key: 'description',
      ellipsis: {
        showTitle: false,
      },
      render: (text) => (
        <Tooltip title={text} overlayStyle={{ maxWidth: '400px' }}>
          <span style={{ cursor: 'pointer' }}>
            {text}
          </span>
        </Tooltip>
      ),
    },
    {
      title: 'Детали',
      dataIndex: 'details',
      key: 'details',
      ellipsis: {
        showTitle: false,
      },
      render: (text) => (
        <Tooltip title={text} overlayStyle={{ maxWidth: '400px' }}>
          <span style={{ cursor: 'pointer' }}>
            {text}
          </span>
        </Tooltip>
      ),
    },
    {
      title: 'Решение',
      dataIndex: 'solution',
      key: 'solution',
      ellipsis: {
        showTitle: false,
      },
      render: (text) => (
        <Tooltip title={text} overlayStyle={{ maxWidth: '400px' }}>
          <span style={{ cursor: 'pointer' }}>
            {text}
          </span>
        </Tooltip>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={items}
      rowKey={(record, index) => index}
      pagination={{ pageSize: 20 }}
      size="small"
      scroll={{ x: 800 }}
    />
  );
};

const Reports = () => {
  const [reports, setReports] = useState([]);
  const [filteredReports, setFilteredReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportDetail, setReportDetail] = useState(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [cleanupConfig, setCleanupConfig] = useState(null);
  const [filters, setFilters] = useState({
    cluster: 'All',
    period: 'All',
    search: ''
  });

  const loadReports = async () => {
    try {
      setLoading(true);
      const response = await getReports();
      setReports(response.data.reports || []);
      setFilteredReports(response.data.reports || []);
    } catch (error) {
      console.error('Ошибка загрузки отчетов:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadCleanupConfig = async () => {
    try {
      const response = await getCleanupConfig();
      setCleanupConfig(response.data);
    } catch (error) {
      console.error('Ошибка загрузки настроек очистки:', error);
    }
  };

  useEffect(() => {
    loadReports();
    loadCleanupConfig();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [reports, filters]);

  const applyFilters = () => {
    let filtered = [...reports];

    // Фильтр по кластеру
    if (filters.cluster !== 'All') {
      filtered = filtered.filter(report => report.cluster_name === filters.cluster);
    }

    // Фильтр по периоду
    const now = new Date();
    if (filters.period !== 'All') {
      const cutoffDate = new Date();
      if (filters.period === 'Today') {
        cutoffDate.setHours(0, 0, 0, 0);
      } else if (filters.period === 'Last 7 days') {
        cutoffDate.setDate(now.getDate() - 7);
      } else if (filters.period === 'Last 30 days') {
        cutoffDate.setDate(now.getDate() - 30);
      }

      filtered = filtered.filter(report => {
        const reportDate = new Date(report.timestamp);
        return reportDate >= cutoffDate;
      });
    }

    // Поиск по имени
    if (filters.search) {
      filtered = filtered.filter(report =>
        report.cluster_name.toLowerCase().includes(filters.search.toLowerCase()) ||
        report.result_id.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    setFilteredReports(filtered);
  };

  const handleViewReport = async (reportId) => {
    try {
      const response = await getReport(reportId);
      setReportDetail(response.data);
      setDetailModalVisible(true);
    } catch (error) {
      console.error('Ошибка загрузки отчета:', error);
    }
  };

  const handleDeleteReport = async (reportId) => {
    try {
      await deleteReport(reportId);
      loadReports();
    } catch (error) {
      console.error('Ошибка удаления отчета:', error);
    }
  };

  const handleExportReport = async (reportId, format) => {
    try {
      const response = await exportReport(reportId, format);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${reportId}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Ошибка экспорта отчета:', error);
    }
  };

  const getStatusTag = (report) => {
    const totalIssues = (report.critical || 0) + (report.warning || 0) + (report.info || 0);
    if (totalIssues === 0) {
      return <Tag color="#50fa7b">OK</Tag>;
    } else if (report.critical > 0) {
      return <Tag color="#ff5555">Критические ошибки</Tag>;
    } else if (report.warning > 0) {
      return <Tag color="#f1fa8c">Предупреждения</Tag>;
    } else {
      return <Tag color="#bd93f9">Другие ошибки</Tag>;
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'result_id',
      key: 'result_id',
      width: 200,
    },
    {
      title: 'Кластер',
      dataIndex: 'cluster_name',
      key: 'cluster_name',
    },
    {
      title: 'Время',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (timestamp) => new Date(timestamp).toLocaleString(),
    },
    {
      title: 'Тип',
      dataIndex: 'inspection_type',
      key: 'inspection_type',
      render: (type) => type === 'immediate' ? 'Немедленная' : 'Запланированная',
    },
    {
      title: 'Статус',
      key: 'status',
      render: (_, record) => getStatusTag(record),
    },
    {
      title: 'Критические',
      dataIndex: 'critical',
      key: 'critical',
      render: (value) => value || 0,
    },
    {
      title: 'Предупреждения',
      dataIndex: 'warning',
      key: 'warning',
      render: (value) => value || 0,
    },
    {
      title: 'Другие',
      dataIndex: 'info',
      key: 'info',
      render: (value) => value || 0,
    },
    {
      title: 'Успешно',
      dataIndex: 'passed',
      key: 'passed',
      render: (value) => value || 0,
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            icon={<EyeOutlined />}
            onClick={() => handleViewReport(record.result_id)}
          >
            Просмотр
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => handleExportReport(record.result_id, 'json')}
          >
            JSON
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => handleExportReport(record.result_id, 'excel')}
          >
            Excel
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => handleExportReport(record.result_id, 'pdf')}
          >
            PDF
          </Button>
          <Button
            icon={<DeleteOutlined />}
            danger
            onClick={() => Modal.confirm({
              title: 'Удалить отчет?',
              content: 'Это действие нельзя отменить',
              onOk: () => handleDeleteReport(record.result_id)
            })}
          >
            Удалить
          </Button>
        </Space>
      ),
    },
  ];

  const clusters = [...new Set(reports.map(r => r.cluster_name))];

  return (
    <div>
      <div className="page-title">Отчеты инспекций</div>
      <div className="page-subtitle">Просмотр и управление отчетами инспекций кластеров</div>

      {cleanupConfig && (
        <Collapse
          style={{ marginBottom: 16 }}
          items={[
            {
              key: 'cleanup-info',
              label: 'Информация об автоочистке отчетов',
              children: (
                <div>
                  <p>Система автоматически удаляет старые отчеты для освобождения дискового пространства.</p>
                  <ul style={{ marginTop: 8 }}>
                    <li><strong>Период хранения:</strong> {cleanupConfig.retention_days || 14} дней</li>
                    <li><strong>Источник настроек:</strong> {cleanupConfig.source === 'env' ? 'Переменная окружения' : cleanupConfig.source === 'file' ? 'Файл конфигурации' : 'По умолчанию'}</li>
                  </ul>
                  <p style={{ marginTop: 8 }}><strong>Примечание:</strong> Автоочистка выполняется автоматически в фоновом режиме. Изменить настройки можно через переменную окружения <code>KUBEYE_REPORT_RETENTION_DAYS</code> или файл конфигурации.</p>
                </div>
              ),
            },
          ]}
        />
      )}

      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            placeholder="Кластер"
            style={{ width: 200 }}
            onChange={(value) => setFilters(prev => ({ ...prev, cluster: value }))}
            value={filters.cluster}
          >
            <Option value="All">Все кластеры</Option>
            {clusters.map(cluster => (
              <Option key={cluster} value={cluster}>{cluster}</Option>
            ))}
          </Select>

          <Select
            placeholder="Период"
            style={{ width: 150 }}
            onChange={(value) => setFilters(prev => ({ ...prev, period: value }))}
            value={filters.period}
          >
            <Option value="All">Все время</Option>
            <Option value="Today">Сегодня</Option>
            <Option value="Last 7 days">Последние 7 дней</Option>
            <Option value="Last 30 days">Последние 30 дней</Option>
          </Select>

          <Search
            placeholder="Поиск по кластеру или ID"
            style={{ width: 250 }}
            onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
            value={filters.search}
          />
        </Space>
      </Card>

      <Card>
        <Table
          columns={columns}
          dataSource={filteredReports}
          loading={loading}
          rowKey="result_id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title="Детали отчета"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={1800}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Закрыть
          </Button>
        ]}
      >
        {reportDetail && (
          <div>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="ID отчета">{reportDetail.result_id}</Descriptions.Item>
              <Descriptions.Item label="Кластер">{reportDetail.cluster_name}</Descriptions.Item>
              <Descriptions.Item label="Время">{new Date(reportDetail.timestamp).toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="Тип инспекции">
                {reportDetail.inspection_type === 'immediate' ? 'Немедленная' : 'Запланированная'}
              </Descriptions.Item>
            </Descriptions>

            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={6}>
                <Statistic title="Критические" value={reportDetail.critical || 0} valueStyle={{ color: '#ff5555' }} />
              </Col>
              <Col span={6}>
                <Statistic title="Предупреждения" value={reportDetail.warning || 0} valueStyle={{ color: '#f1fa8c' }} />
              </Col>
              <Col span={6}>
                <Statistic title="Другие ошибки" value={reportDetail.info || 0} valueStyle={{ color: '#bd93f9' }} />
              </Col>
              <Col span={6}>
                <Statistic title="Успешно" value={reportDetail.passed || 0} valueStyle={{ color: '#50fa7b' }} />
              </Col>
            </Row>

            <div style={{ marginTop: 24 }}>
              <Tabs defaultActiveKey="details" items={[
                {
                  key: 'details',
                  label: 'Детали результатов инспекции',
                  children: <InspectionDetails items={getInspectionItems(reportDetail)} />
                },
                {
                  key: 'cleanup-info',
                  label: 'Информация об автоочистке отчетов',
                  children: (
                    <div>
                      <p>Система автоматически удаляет старые отчеты для освобождения дискового пространства.</p>
                      <div style={{ marginTop: 16 }}>
                        <strong>Текущие настройки автоочистки:</strong>
                        <ul style={{ marginTop: 8 }}>
                          <li>Период хранения: {cleanupConfig?.retention_days || 14} дней</li>
                          <li>Источник настроек: {cleanupConfig?.source === 'env' ? 'Переменная окружения' : cleanupConfig?.source === 'file' ? 'Файл конфигурации' : 'По умолчанию'}</li>
                        </ul>
                      </div>
                      <div style={{ marginTop: 16 }}>
                        <p><strong>Примечание:</strong> Автоочистка выполняется автоматически в фоновом режиме. Изменить настройки можно через переменную окружения <code>KUBEYE_REPORT_RETENTION_DAYS</code> или файл конфигурации.</p>
                      </div>
                    </div>
                  )
                }
              ]} />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Reports;