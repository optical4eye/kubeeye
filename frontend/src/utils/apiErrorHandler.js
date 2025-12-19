// utils/apiErrorHandler.js
// Централизованная обработка ошибок API

export const handleApiError = (error, defaultMessage = 'Произошла ошибка') => {
  let errorMessage = defaultMessage;

  if (error.response) {
    // Ошибка от сервера
    const responseData = error.response.data;

    if (typeof responseData === 'string') {
      errorMessage = responseData;
    } else if (responseData?.detail) {
      if (typeof responseData.detail === 'string') {
        errorMessage = responseData.detail;
      } else if (typeof responseData.detail === 'object') {
        errorMessage = responseData.detail.message || responseData.detail.error || JSON.stringify(responseData.detail);
      } else {
        errorMessage = String(responseData.detail);
      }
    } else if (responseData?.message) {
      errorMessage = responseData.message;
    } else if (responseData?.error) {
      errorMessage = responseData.error;
    } else {
      // Если данные - объект без известных полей
      errorMessage = JSON.stringify(responseData);
    }
  } else if (error.request) {
    // Нет ответа от сервера
    errorMessage = 'Сетевая ошибка: сервер не отвечает';
  } else {
    // Другие ошибки
    errorMessage = error.message || defaultMessage;
  }

  return errorMessage;
};

export const fetchData = async (fetchFn, errorMessage, onSuccess) => {
  try {
    const response = await fetchFn();
    if (onSuccess && typeof onSuccess === 'function') {
      onSuccess(response.data);
    }
    return response.data;
  } catch (error) {
    const processedError = handleApiError(error, errorMessage);
    console.error('API Error:', error);
    throw new Error(processedError);
  }
};

export const apiRequest = async (requestFn, successMessage = null, errorMessage = 'Произошла ошибка') => {
  try {
    const response = await requestFn();
    if (successMessage) {
      console.log(successMessage);
    }
    return response.data;
  } catch (error) {
    const processedError = handleApiError(error, errorMessage);
    console.error('API Request Error:', error);
    throw new Error(processedError);
  }
};