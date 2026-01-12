// utils/nodeParser.js
// Утилиты для парсинга и форматирования данных узлов

export const parseNodesFromText = text => {
  const nodes = [];
  const lines = text.split('\n').filter(line => line.trim());

  for (const line of lines) {
    const parts = line.trim().split(/\s+/);
    if (parts.length >= 3) {
      const [ip_port, user, auth_type, ...auth_data] = parts;
      const [ip, port_str] = ip_port.split(':');
      const port = parseInt(port_str) || 22;
      const auth_data_str = auth_data.join(' ') || '';

      const node = {
        ip,
        port,
        username: user,
        auth_type,
      };

      if (auth_type === 'password') {
        node.password = auth_data_str;
      } else if (auth_type === 'key') {
        node.ssh_key = auth_data_str;
      }

      nodes.push(node);
    }
  }

  return nodes;
};

export const formatNodesForText = nodes => {
  return nodes
    .map(node => {
      const ip_port = `${node.ip}:${node.port}`;
      const auth_data = node.auth_type === 'password' ? node.password : node.ssh_key;
      return `${ip_port} ${node.username} ${node.auth_type} ${auth_data || ''}`.trim();
    })
    .join('\n');
};

export const validateNodeFormat = text => {
  const lines = text.split('\n').filter(line => line.trim());

  for (const line of lines) {
    const parts = line.trim().split(/\s+/);
    if (parts.length < 3) {
      return false;
    }

    const [ip_port, , auth_type] = parts;
    if (!ip_port.includes(':')) {
      return false;
    }

    if (auth_type !== 'password' && auth_type !== 'key') {
      return false;
    }
  }

  return true;
};
