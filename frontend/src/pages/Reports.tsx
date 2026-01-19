import React, { useState, useEffect } from 'react';
import { Collapse } from 'antd';
import {
  getReports,
  getReport,
  deleteReport,
  exportReport,
  getCleanupConfig,
} from '../services/api';
import { useReportsFilters } from '../hooks/useReportsFilters';
import ReportsFilters from '../components/ReportsFilters';
import ReportsTable from '../components/ReportsTable';
import ReportDetailsModal from '../components/ReportDetailsModal';

const Reports: React.FC = React.memo(() => {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [reportDetail, setReportDetail] = useState<any>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [cleanupConfig, setCleanupConfig] = useState<any>(null);

  const { filteredReports, filters, setFilters } = useReportsFilters(reports);

  const loadReports = async () => {
    try {
      setLoading(true);
      const response = await getReports();
      setReports(response.data.reports || []);
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

    // Listen for new report events
    const handleNewReport = () => {
      loadReports();
    };

    window.addEventListener('newReportAvailable', handleNewReport);

    return () => {
      window.removeEventListener('newReportAvailable', handleNewReport);
    };
  }, []);

  const handleViewReport = async (reportId: string) => {
    try {
      const response = await getReport(reportId);
      setReportDetail(response.data);
      setDetailModalVisible(true);
    } catch (error) {
      console.error('Ошибка загрузки отчета:', error);
    }
  };

  const handleDeleteReport = async (reportId: string) => {
    try {
      await deleteReport(reportId);
      loadReports();
    } catch (error) {
      console.error('Ошибка удаления отчета:', error);
    }
  };

  const handleExportReport = async (reportId: string, format: string) => {
    try {
      const response = await exportReport(reportId, format);
      const url = window.URL.createObjectURL(new Blob([response.data]));

      // Determine filename based on report type
      const report = reports.find(r => r.result_id === reportId);
      const filename =
        report && report.inspection_type === 'popeye'
          ? `popeye_${reportId}.${format}`
          : `${reportId}.${format}`;

      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Ошибка экспорта отчета:', error);
    }
  };

  const clusters = [...new Set(reports.map(r => r.cluster_name))];

  return (
    <div>
      <div className="page-title">Отчеты инспекций</div>
      <div className="page-subtitle">Просмотр и управление отчетами инспекций кластеров</div>

      {cleanupConfig && (
        <Collapse
          className="margin-bottom-space-4"
          items={[
            {
              key: 'cleanup-info',
              label: 'Информация об автоочистке отчетов',
              children: (
                <div>
                  <p>
                    Система автоматически удаляет старые отчеты для освобождения дискового
                    пространства.
                  </p>
                  <ul className="margin-top-space-2">
                    <li>
                      <strong>Период хранения:</strong> {cleanupConfig.retention_days} дней
                    </li>
                  </ul>
                  <p className="margin-top-space-2">
                    <strong>Примечание:</strong> Автоочистка выполняется автоматически в фоновом
                    режиме. Изменить настройки можно через переменную окружения{' '}
                    <code>KUBEEYE_REPORT_RETENTION_DAYS</code> или файл конфигурации.
                  </p>
                </div>
              ),
            },
          ]}
        />
      )}

      <ReportsFilters clusters={clusters} filters={filters} setFilters={setFilters} />

      <ReportsTable
        filteredReports={filteredReports}
        loading={loading}
        onView={handleViewReport}
        onDelete={handleDeleteReport}
        onExport={handleExportReport}
      />

      <ReportDetailsModal
        visible={detailModalVisible}
        onClose={() => setDetailModalVisible(false)}
        reportDetail={reportDetail}
      />
    </div>
  );
});

Reports.displayName = 'Reports';

export default Reports;
