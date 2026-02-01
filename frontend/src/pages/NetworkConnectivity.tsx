import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Select,
  Checkbox,
  Input,
  InputNumber,
  Button,
  Table,
  App,
  Space,
  Alert,
} from 'antd';
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  checkNetworkConnectivity,
  getClustersForNetworkCheck,
  exportNetworkCheckResult,
} from '../services/api';
import { getStatusTag } from '../components/ui/statusUtils';

const { Option } = Select;

const NetworkConnectivity = () => {
  const { t } = useTranslation();
  const { message: messageApi } = App.useApp();
  const [clusters, setClusters] = useState([]);
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [selectedNodes, setSelectedNodes] = useState([]);
  const [targetIp, setTargetIp] = useState('');
  const [targetPort, setTargetPort] = useState<number | null>(null);
  const [timeout, setTimeout] = useState<number>(3);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [results, setResults] = useState([]);
  const [resultId, setResultId] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadClusters();
  }, []);

  const loadClusters = async () => {
    try {
      setLoading(true);
      const response = await getClustersForNetworkCheck();
      setClusters(response.data.clusters || []);
    } catch {
      messageApi.error(t('networkPage.messages.loadClustersError'));
    } finally {
      setLoading(false);
    }
  };

  const handleNodeSelection = (nodeIp, checked) => {
    if (checked) {
      setSelectedNodes([...selectedNodes, nodeIp]);
    } else {
      setSelectedNodes(selectedNodes.filter(ip => ip !== nodeIp));
    }
  };

  const handleSelectAllNodes = checked => {
    if (checked) {
      const cluster = clusters.find(c => c.name === selectedCluster);
      if (cluster) {
        setSelectedNodes(cluster.nodes.map(node => node.ip));
      }
    } else {
      setSelectedNodes([]);
    }
  };

  const validateForm = () => {
    if (!selectedCluster) {
      messageApi.error(t('networkPage.messages.selectCluster'));
      return false;
    }
    if (selectedNodes.length === 0) {
      messageApi.error(t('networkPage.messages.selectNode'));
      return false;
    }
    if (!targetIp) {
      messageApi.error(t('networkPage.messages.enterIp'));
      return false;
    }
    if (!targetPort) {
      messageApi.error(t('networkPage.messages.enterPort'));
      return false;
    }
    if (targetPort < 1 || targetPort > 65535) {
      messageApi.error(t('networkPage.messages.portRange'));
      return false;
    }
    return true;
  };

  const handleCheckConnectivity = async () => {
    if (!validateForm()) return;

    try {
      setChecking(true);
      setResults([]);
      setResultId(null);

      const checkData = {
        cluster_name: selectedCluster,
        selected_nodes: selectedNodes,
        target_ip: targetIp,
        target_port: targetPort,
        timeout: timeout,
      };

      const response = await checkNetworkConnectivity(checkData);
      const { result_id, results: checkResults } = response.data;

      setResults(checkResults);
      setResultId(result_id);

      const successCount = checkResults.filter(r => r.status === 'success').length;
      const failCount = checkResults.filter(r => r.status === 'failed').length;

      if (failCount === 0) {
        messageApi.success(t('networkPage.messages.allSuccessful', { count: successCount }));
      } else if (successCount === 0) {
        messageApi.error(t('networkPage.messages.allFailed', { count: failCount }));
      } else {
        messageApi.warning(
          t('networkPage.messages.mixed', { success: successCount, fail: failCount })
        );
      }
    } catch {
      messageApi.error(t('networkPage.messages.checkError'));
    } finally {
      setChecking(false);
    }
  };

  const exportResults = async format => {
    if (!resultId) {
      messageApi.warning(t('networkPage.messages.noResults'));
      return;
    }

    try {
      const response = await exportNetworkCheckResult(resultId, format);

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `network_check_${selectedCluster}_${timestamp}.${format}`;
      link.setAttribute('download', filename);

      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      messageApi.success(t('networkPage.messages.exported', { format: format.toUpperCase() }));
    } catch {
      messageApi.error(t('networkPage.messages.exportError'));
    }
  };

  const getStatusIcon = status => {
    switch (status) {
      case 'success':
        return (
          <CheckCircleOutlined
            aria-label="Success status"
            style={{ color: 'var(--status-completed)' }}
          />
        );
      case 'failed':
        return (
          <CloseCircleOutlined aria-label="Failed status" style={{ color: 'var(--error-color)' }} />
        );
      default:
        return (
          <ClockCircleOutlined
            aria-label="Pending status"
            style={{ color: 'var(--status-pending)' }}
          />
        );
    }
  };

  const resultColumns = [
    {
      title: t('networkPage.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: status => (
        <Space>
          {getStatusIcon(status)}
          {getStatusTag(status)}
        </Space>
      ),
      width: 120,
    },
    {
      title: t('networkPage.columns.node'),
      dataIndex: 'node_ip',
      key: 'node_ip',
      render: ip => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{ip}</div>
        </div>
      ),
    },
    {
      title: t('networkPage.columns.target'),
      key: 'target',
      render: (_, record) => `${record.target_ip}:${record.target_port}`,
    },
    {
      title: t('networkPage.columns.responseTime'),
      dataIndex: 'response_time',
      key: 'response_time',
      render: time => `${time}s`,
      width: 120,
    },
    {
      title: t('networkPage.columns.error'),
      dataIndex: 'error',
      key: 'error',
      render: error => (error ? <span style={{ color: 'var(--error-color)' }}>{error}</span> : '-'),
    },
  ];

  const selectedClusterData = clusters.find(c => c.name === selectedCluster);

  return (
    <>
      <div>
      <div className="page-title">{t('networkPage.title')}</div>
      <div className="page-subtitle">{t('networkPage.subtitle')}</div>

      <Space direction="vertical" size="large" className="kube-width-100">
        <Card
          title={t('networkPage.settings')}
          loading={loading}
          className="kube-width-100"
          bodyStyle={{ width: '100%' }}
        >
          <Form form={form} layout="vertical" style={{ width: '100%' }}>
            <Form.Item name="cluster" label={t('networkPage.cluster')} required>
              <Select
                className="margin-top-space-2"
                style={{ width: '100%' }}
                placeholder={t('networkPage.selectClusterPlaceholder')}
                onChange={setSelectedCluster}
                value={selectedCluster}
              >
                {clusters.map(cluster => (
                  <Option key={cluster.name} value={cluster.name}>
                    {cluster.name} ({cluster.nodes.length} {t('networkPage.nodes')})
                  </Option>
                ))}
              </Select>
            </Form.Item>

            {selectedClusterData && (
              <Form.Item label={t('networkPage.nodesForCheck')} required>
                <div className="border-form">
                  <Checkbox
                    onChange={e => handleSelectAllNodes(e.target.checked)}
                    checked={selectedNodes.length === selectedClusterData.nodes.length}
                    indeterminate={
                      selectedNodes.length > 0 &&
                      selectedNodes.length < selectedClusterData.nodes.length
                    }
                    style={{ marginBottom: '8px', fontWeight: 'bold' }}
                  >
                    {t('networkPage.selectAllNodes')}
                  </Checkbox>
                  <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                    {selectedClusterData.nodes.map(node => (
                      <div key={node.ip} style={{ marginBottom: '4px' }}>
                        <Checkbox
                          checked={selectedNodes.includes(node.ip)}
                          onChange={e => handleNodeSelection(node.ip, e.target.checked)}
                        >
                          {node.name} ({node.ip}:{node.port})
                        </Checkbox>
                      </div>
                    ))}
                  </div>
                </div>
                {selectedNodes.length > 0 && (
                  <div
                    style={{ marginTop: '8px', fontSize: '12px', color: 'var(--neutral-color)' }}
                  >
                    {t('networkPage.selectedNodesCount', { count: selectedNodes.length })}
                  </div>
                )}
              </Form.Item>
            )}

            <Space>
              <Form.Item name="target_ip" label={t('networkPage.targetIp')} required>
                <Input
                  placeholder="192.168.1.100"
                  value={targetIp}
                  onChange={e => setTargetIp(e.target.value)}
                  className="width-150"
                />
              </Form.Item>

              <Form.Item name="target_port" label={t('networkPage.port')} required>
                <InputNumber
                  placeholder="80"
                  value={targetPort}
                  onChange={value => setTargetPort(value)}
                  className="width-100px"
                  min={1}
                  max={65535}
                />
              </Form.Item>

              <Form.Item name="timeout" label={t('networkPage.timeout')}>
                <InputNumber
                  min={1}
                  max={30}
                  value={timeout}
                  onChange={value => setTimeout(value)}
                  className="width-120px"
                  placeholder="3"
                />
              </Form.Item>
            </Space>

            <Form.Item>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleCheckConnectivity}
                loading={checking}
                disabled={!selectedCluster || selectedNodes.length === 0}
              >
                {checking ? t('networkPage.checking') : t('networkPage.checkConnectivity')}
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {results.length > 0 && (
          <Card
            title={t('networkPage.resultsTitle', { count: results.length })}
            extra={
              resultId && (
                <Space wrap>
                  <Button onClick={() => exportResults('json')}>
                    {t('networkPage.exportJson')}
                  </Button>
                </Space>
              )
            }
          >
            <Table
              columns={resultColumns}
              dataSource={results}
              rowKey={record => `${record.node_ip}-${record.target_ip}-${record.target_port}`}
              pagination={false}
              size="small"
            />

            <div className="margin-top-space-4">
              <Alert
                message={t('networkPage.statisticsMessage', {
                  success: results.filter(r => r.status === 'success').length,
                  fail: results.filter(r => r.status === 'failed').length,
                })}
                type={results.some(r => r.status === 'failed') ? 'warning' : 'success'}
                showIcon
              />
            </div>
          </Card>
        )}
      </Space>
    </div>
    </>
  );
};

export default NetworkConnectivity;
