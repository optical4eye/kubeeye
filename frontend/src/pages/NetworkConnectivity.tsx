import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Select,
  Checkbox,
  Input,
  Button,
  Table,
  message,
  Space,
  Tag,
  Alert,
} from 'antd';
import {
  WifiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import {
  checkNetworkConnectivity,
  getClustersForNetworkCheck,
  exportNetworkCheckResult,
} from '../services/api';
import { getStatusTag } from '../components/statusUtils';

const { Option } = Select;

const NetworkConnectivity = () => {
  const [clusters, setClusters] = useState([]);
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [selectedNodes, setSelectedNodes] = useState([]);
  const [targetIp, setTargetIp] = useState('');
  const [targetPort, setTargetPort] = useState('');
  const [timeout, setTimeout] = useState(5);
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
    } catch (error) {
      message.error('Ошибка загрузки кластеров');
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
      message.error('Выберите кластер');
      return false;
    }
    if (selectedNodes.length === 0) {
      message.error('Выберите хотя бы один узел');
      return false;
    }
    if (!targetIp) {
      message.error('Введите IP-адрес');
      return false;
    }
    if (!targetPort) {
      message.error('Введите порт');
      return false;
    }
    const portNum = parseInt(targetPort);
    if (isNaN(portNum) || portNum < 1 || portNum > 65535) {
      message.error('Порт должен быть числом от 1 до 65535');
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
        target_port: parseInt(targetPort),
        timeout: timeout,
      };

      const response = await checkNetworkConnectivity(checkData);
      const { result_id, results: checkResults } = response.data;

      setResults(checkResults);
      setResultId(result_id);

      const successCount = checkResults.filter(r => r.status === 'success').length;
      const failCount = checkResults.filter(r => r.status === 'failed').length;

      if (failCount === 0) {
        message.success(`Все проверки успешны (${successCount})`);
      } else if (successCount === 0) {
        message.error(`Все проверки неудачны (${failCount})`);
      } else {
        message.warning(`${successCount} успешных, ${failCount} неудачных проверок`);
      }
    } catch (error) {
      message.error('Ошибка выполнения проверки подключения');
    } finally {
      setChecking(false);
    }
  };

  const exportResults = async format => {
    if (!resultId) {
      message.warning('Нет сохраненных результатов для экспорта');
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

      message.success(`Результаты экспортированы в ${format.toUpperCase()}`);
    } catch (error) {
      message.error('Ошибка экспорта результатов');
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
      title: 'Статус',
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
      title: 'Узел',
      dataIndex: 'node_ip',
      key: 'node_ip',
      render: ip => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{ip}</div>
        </div>
      ),
    },
    {
      title: 'Цель',
      key: 'target',
      render: (_, record) => `${record.target_ip}:${record.target_port}`,
    },
    {
      title: 'Время ответа',
      dataIndex: 'response_time',
      key: 'response_time',
      render: time => `${time}s`,
      width: 120,
    },
    {
      title: 'Ошибка',
      dataIndex: 'error',
      key: 'error',
      render: error => (error ? <span style={{ color: 'var(--error-color)' }}>{error}</span> : '-'),
    },
  ];

  const selectedClusterData = clusters.find(c => c.name === selectedCluster);

  return (
    <div>
      <div className="page-title">Проверка сетевых подключений</div>
      <div className="page-subtitle">Проверка доступности сетевых сервисов из узлов кластера</div>

      <Space direction="vertical" size="large" className="kube-width-100">
        <Card title="Настройки проверки" loading={loading} className="kube-width-100" bodyStyle={{ width: '100%' }}>
          <Form form={form} layout="vertical" style={{ width: '100%' }}>
            <Form.Item name="cluster" label="Кластер" required>
              <Select
                className="margin-top-space-2"
                style={{ width: '100%' }}
                placeholder="Выберите кластер"
                onChange={setSelectedCluster}
                value={selectedCluster}
              >
                {clusters.map(cluster => (
                  <Option key={cluster.name} value={cluster.name}>
                    {cluster.name} ({cluster.nodes.length} узлов)
                  </Option>
                ))}
              </Select>
            </Form.Item>

            {selectedClusterData && (
              <Form.Item label="Узлы для проверки" required>
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
                    Выбрать все узлы
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
                    Выбрано узлов: {selectedNodes.length}
                  </div>
                )}
              </Form.Item>
            )}

            <Space>
              <Form.Item name="target_ip" label="Целевой IP" required>
                <Input
                  placeholder="192.168.1.100"
                  value={targetIp}
                  onChange={e => setTargetIp(e.target.value)}
                  className="width-150"
                />
              </Form.Item>

              <Form.Item name="target_port" label="Порт" required>
                <Input
                  placeholder="80"
                  value={targetPort}
                  onChange={e => setTargetPort(e.target.value)}
                  className="width-100px"
                />
              </Form.Item>

              <Form.Item name="timeout" label="Таймаут (сек)">
                <Input
                  type="number"
                  min={1}
                  max={30}
                  value={timeout}
                  onChange={e => setTimeout(parseInt(e.target.value) || 5)}
                  className="width-120px"
                />
              </Form.Item>
            </Space>

            <Form.Item>
              <Button
                type="primary"
                icon={<WifiOutlined />}
                onClick={handleCheckConnectivity}
                loading={checking}
                disabled={!selectedCluster || selectedNodes.length === 0}
              >
                {checking ? 'Проверка...' : 'Проверить подключение'}
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {results.length > 0 && (
          <Card
            title={`Результаты проверки (${results.length} узлов)`}
            extra={
              resultId && (
                <Space wrap>
                  <Button onClick={() => exportResults('json')}>Экспорт JSON</Button>
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
                message={`Статистика: ${results.filter(r => r.status === 'success').length} успешных, ${results.filter(r => r.status === 'failed').length} неудачных`}
                type={results.some(r => r.status === 'failed') ? 'warning' : 'success'}
                showIcon
              />
            </div>
          </Card>
        )}
      </Space>
    </div>
  );
};

export default NetworkConnectivity;
