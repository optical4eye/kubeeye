import React, { useState, useEffect } from 'react';
import { Collapse } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  getReports,
  getReport,
  deleteReport,
  exportReport,
  getCleanupConfig,
} from '../services/api';
import { useReportsFilters } from '../hooks/useReportsFilters';
import { ReportsFilters, ReportsTable, ReportDetailsModal } from '../components/reports';

const Reports: React.FC = React.memo(() => {
  const { t } = useTranslation();
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
    } catch {
      // Error loading reports
    } finally {
      setLoading(false);
    }
  };

  const loadCleanupConfig = async () => {
    try {
      const response = await getCleanupConfig();
      setCleanupConfig(response.data);
    } catch {
      // Error loading cleanup config
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
    } catch {
      // Error loading report
    }
  };

  const handleDeleteReport = async (reportId: string) => {
    try {
      await deleteReport(reportId);
      loadReports();
    } catch {
      // Error deleting report
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
    } catch {
      // Error exporting report
    }
  };

  const clusters = [...new Set(reports.map(r => r.cluster_name))];

  return (
    <div>
      <div className="page-title">{t('reports.title')}</div>
      <div className="page-subtitle">{t('reports.subtitle')}</div>

      {cleanupConfig && (
        <Collapse
          className="margin-bottom-space-4"
          items={[
            {
              key: 'cleanup-info',
              label: t('reports.cleanupInfo'),
              children: (
                <div>
                  <p>{t('reports.autoDelete')}</p>
                  <ul className="margin-top-space-2">
                    <li>
                      <strong>{t('reports.retentionPeriod')}</strong> {cleanupConfig.retention_days}{' '}
                      {t('clusters.days')}
                    </li>
                  </ul>
                  <p className="margin-top-space-2">
                    <strong>{t('reports.note')}</strong> {t('reports.autoCleanup')}
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
        open={detailModalVisible}
        onClose={() => setDetailModalVisible(false)}
        reportDetail={reportDetail}
      />
    </div>
  );
});

Reports.displayName = 'Reports';

export default Reports;
