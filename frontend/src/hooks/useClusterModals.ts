import { useState } from 'react';

export const useClusterModals = () => {
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [detailsModalVisible, setDetailsModalVisible] = useState(false);

  const openEditModal = () => setEditModalVisible(true);
  const closeEditModal = () => setEditModalVisible(false);
  const openDetailsModal = () => setDetailsModalVisible(true);
  const closeDetailsModal = () => setDetailsModalVisible(false);

  return {
    editModalVisible,
    detailsModalVisible,
    openEditModal,
    closeEditModal,
    openDetailsModal,
    closeDetailsModal,
  };
};
