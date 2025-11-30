import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './Home.css';

function Home() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [user, setUser] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null); // 'uploading', 'success', 'error'
  const [uploadMessage, setUploadMessage] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [location, setLocation] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [tasks, setTasks] = useState([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);
  const [tasksError, setTasksError] = useState('');
  const [selectedTask, setSelectedTask] = useState(null);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [isLoadingTaskDetail, setIsLoadingTaskDetail] = useState(false);
  const [taskDetailError, setTaskDetailError] = useState('');

  useEffect(() => {
    // localStorage에서 사용자 정보 가져오기
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    }
    // task 목록 가져오기
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    setIsLoadingTasks(true);
    setTasksError('');
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5000/video/tasks', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      const data = await response.json();

      console.log(data);

      if (!response.ok) {
        setTasksError(data.message || 'Task 목록을 불러오는데 실패했습니다.');
        setIsLoadingTasks(false);
        return;
      }

      // API 응답이 task_ids 배열이거나 task 객체 배열일 수 있음
      if (data.task_ids) {
        // task_ids가 문자열 배열인 경우
        if (typeof data.task_ids[0] === 'string') {
          setTasks(data.task_ids.map(taskId => ({ task_id: taskId, status: 'PROCESSING' })));
        } else {
          // task_ids가 객체 배열인 경우 (task_id, status 포함)
          setTasks(data.task_ids);
        }
      } else if (data.tasks) {
        // tasks 필드로 오는 경우
        setTasks(data.tasks);
      } else {
        setTasks([]);
      }
      setIsLoadingTasks(false);
    } catch (err) {
      console.error('Fetch tasks error:', err);
      setTasksError('서버에 연결할 수 없습니다.');
      setIsLoadingTasks(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login', { replace: true });
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      // 동영상 파일인지 확인
      if (file.type.startsWith('video/')) {
        setSelectedFile(file);
        setUploadStatus(null);
        setUploadMessage('');
      } else {
        setUploadStatus('error');
        setUploadMessage('동영상 파일만 업로드 가능합니다.');
      }
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadStatus('error');
      setUploadMessage('파일을 선택해주세요.');
      return;
    }

    if (!location || !date || !time) {
      setUploadStatus('error');
      setUploadMessage('지역, 날짜, 시간을 모두 입력해주세요.');
      return;
    }

    setIsUploading(true);
    setUploadStatus('uploading');
    setUploadMessage('업로드 중...');

    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('video', selectedFile);
      formData.append('location', location);
      formData.append('date', date);
      formData.append('time', time);

      const response = await fetch('http://localhost:5000/video/video', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setUploadStatus('error');
        setUploadMessage(data.message || '업로드에 실패했습니다.');
        setIsUploading(false);
        return;
      }

      // 업로드 성공
      setUploadStatus('success');
      setUploadMessage('동영상이 성공적으로 업로드되었습니다!');
      setSelectedFile(null);
      setLocation('');
      setDate('');
      setTime('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      setIsUploading(false);
      
      // 업로드 성공 후 task 목록 새로고침
      setTimeout(() => {
        fetchTasks();
      }, 1000);

    } catch (err) {
      console.error('Upload error:', err);
      setUploadStatus('error');
      setUploadMessage('서버에 연결할 수 없습니다. 나중에 다시 시도해주세요.');
      setIsUploading(false);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setUploadStatus(null);
    setUploadMessage('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const getStatusText = (status) => {
    const statusMap = {
      'PROCESSING': '처리 중',
      'COMPLETED': '완료',
      'FAIL': '실패',
      'DELETED': '삭제됨'
    };
    return statusMap[status] || status;
  };

  const handleTaskClick = async (taskId) => {
    setIsTaskModalOpen(true);
    setIsLoadingTaskDetail(true);
    setTaskDetailError('');
    setSelectedTask(null);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://127.0.0.1:5000/async/tasks/${taskId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        setTaskDetailError(data.message || 'Task 정보를 불러오는데 실패했습니다.');
        setIsLoadingTaskDetail(false);
        return;
      }

      setSelectedTask(data);
      setIsLoadingTaskDetail(false);
    } catch (err) {
      console.error('Fetch task detail error:', err);
      setTaskDetailError('서버에 연결할 수 없습니다.');
      setIsLoadingTaskDetail(false);
    }
  };

  const handleCloseModal = () => {
    setIsTaskModalOpen(false);
    setSelectedTask(null);
    setTaskDetailError('');
  };

  return (
    <div className="home-container">
      <header className="home-header">
        <div className="header-content">
          <h1>홈</h1>
          <div className="user-info">
            {user && (
              <span className="welcome-text">
                환영합니다, {user.user_id || user.name || '사용자'}님!
              </span>
            )}
            <button onClick={handleLogout} className="logout-button">
              로그아웃
            </button>
          </div>
        </div>
      </header>

      <main className="home-main">
        <div className="home-content">
          <div className="welcome-card">
            <h2>로그인에 성공했습니다!</h2>
            <p>홈 페이지에 오신 것을 환영합니다.</p>
          </div>

          <div className="upload-card">
            <h3>동영상 업로드</h3>
            <div className="upload-section">
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
              
              <button
                onClick={handleUploadClick}
                className="select-file-button"
                disabled={isUploading}
              >
                파일 선택
              </button>

              {selectedFile && (
                <div className="selected-file">
                  <div className="file-info">
                    <span className="file-name">{selectedFile.name}</span>
                    <span className="file-size">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </span>
                  </div>
                  <button
                    onClick={handleRemoveFile}
                    className="remove-file-button"
                    disabled={isUploading}
                  >
                    ✕
                  </button>
                </div>
              )}

              <div className="upload-form-fields">
                <div className="form-field-group">
                  <label htmlFor="location">지역 *</label>
                  <input
                    type="text"
                    id="location"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="예: 서울시 강남구"
                    disabled={isUploading}
                    required
                  />
                </div>

                <div className="form-field-group">
                  <label htmlFor="date">날짜 *</label>
                  <input
                    type="date"
                    id="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    disabled={isUploading}
                    required
                  />
                </div>

                <div className="form-field-group">
                  <label htmlFor="time">시간 *</label>
                  <input
                    type="time"
                    id="time"
                    value={time}
                    onChange={(e) => setTime(e.target.value)}
                    disabled={isUploading}
                    required
                  />
                </div>
              </div>

              {selectedFile && (
                <button
                  onClick={handleUpload}
                  className="upload-button"
                  disabled={isUploading}
                >
                  {isUploading ? '업로드 중...' : '업로드'}
                </button>
              )}

              {uploadStatus && (
                <div className={`upload-message ${uploadStatus}`}>
                  {uploadMessage}
                </div>
              )}
            </div>
          </div>

          <div className="tasks-card">
            <div className="tasks-header">
              <h3>동영상 처리 작업</h3>
              <button
                onClick={fetchTasks}
                className="refresh-button"
                disabled={isLoadingTasks}
              >
                {isLoadingTasks ? '새로고침 중...' : '새로고침'}
              </button>
            </div>
            
            {isLoadingTasks && tasks.length === 0 ? (
              <div className="tasks-loading">로딩 중...</div>
            ) : tasksError ? (
              <div className="tasks-error">{tasksError}</div>
            ) : tasks.length === 0 ? (
              <div className="tasks-empty">처리 중인 작업이 없습니다.</div>
            ) : (
              <div className="tasks-list">
                {tasks.map((task, index) => {
                  const taskId = typeof task === 'string' ? task : task.task_id;
                  const status = typeof task === 'string' ? 'PROCESSING' : (task.status || 'PROCESSING');
                  
                  return (
                    <div 
                      key={taskId} 
                      className="task-item"
                      onClick={() => handleTaskClick(taskId)}
                      style={{ cursor: 'pointer' }}
                    >
                      <div className="task-info">
                        <span className="task-number">#{index + 1}</span>
                        <span className="task-id">{taskId}</span>
                      </div>
                      <span className={`task-status task-status-${status.toLowerCase()}`}>
                        {getStatusText(status)}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
            
            {tasks.length > 0 && (
              <div className="tasks-summary">
                총 {tasks.length}개의 작업이 있습니다.
              </div>
            )}
          </div>

          {user && (
            <div className="user-card">
              <h3>사용자 정보</h3>
              <div className="user-details">
                {Object.entries(user).map(([key, value]) => (
                  <div key={key} className="detail-item">
                    <span className="detail-label">{key}:</span>
                    <span className="detail-value">{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Task 상세 정보 모달 */}
      {isTaskModalOpen && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>작업 상세 정보</h2>
              <button className="modal-close-button" onClick={handleCloseModal}>
                ✕
              </button>
            </div>

            <div className="modal-body">
              {isLoadingTaskDetail ? (
                <div className="modal-loading">로딩 중...</div>
              ) : taskDetailError ? (
                <div className="modal-error">{taskDetailError}</div>
              ) : selectedTask ? (
                <div className="task-detail">
                  {/* Task 기본 정보 */}
                  <div className="detail-section">
                    <h3>작업 정보</h3>
                    <div className="detail-grid">
                      <div className="detail-row">
                        <span className="detail-label">Task ID:</span>
                        <span className="detail-value">{selectedTask.task_id}</span>
                      </div>
                      <div className="detail-row">
                        <span className="detail-label">상태:</span>
                        <span className={`detail-value status-badge status-${selectedTask.state?.toLowerCase()}`}>
                          {selectedTask.state || 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Video 정보 */}
                  {selectedTask.video && (
                    <div className="detail-section">
                      <h3>동영상 정보</h3>
                      <div className="detail-grid">
                        <div className="detail-row">
                          <span className="detail-label">Video ID:</span>
                          <span className="detail-value">{selectedTask.video.video_id}</span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">지역:</span>
                          <span className="detail-value">{selectedTask.video.region || 'N/A'}</span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">촬영 일시:</span>
                          <span className="detail-value">{selectedTask.video.recorded_at || 'N/A'}</span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">파일 경로:</span>
                          <span className="detail-value">{selectedTask.video.file_path || 'N/A'}</span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">상태:</span>
                          <span className={`detail-value status-badge status-${selectedTask.video.status?.toLowerCase()}`}>
                            {getStatusText(selectedTask.video.status) || 'N/A'}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Vehicle Counts 정보 */}
                  {selectedTask.vehicle_counts && (
                    <div className="detail-section">
                      <h3>차량 통계</h3>
                      <div className="detail-grid">
                        <div className="detail-row">
                          <span className="detail-label">Vehicle Count ID:</span>
                          <span className="detail-value">{selectedTask.vehicle_counts.vehicle_count_id}</span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">총 정방향:</span>
                          <span className="detail-value">{selectedTask.vehicle_counts.total_forward || 0}대</span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">총 역방향:</span>
                          <span className="detail-value">{selectedTask.vehicle_counts.total_backward || 0}대</span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">집계 일시:</span>
                          <span className="detail-value">{selectedTask.vehicle_counts.counted_at || 'N/A'}</span>
                        </div>

                        {/* 정방향 차종별 통계 */}
                        {selectedTask.vehicle_counts.per_class_forward && (
                          <div className="detail-subsection">
                            <h4>정방향 차종별</h4>
                            <div className="class-counts">
                              {Object.entries(selectedTask.vehicle_counts.per_class_forward).map(([vehicleType, count]) => (
                                <div key={vehicleType} className="class-count-item">
                                  <span className="class-name">{vehicleType}:</span>
                                  <span className="class-count">{count}대</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 역방향 차종별 통계 */}
                        {selectedTask.vehicle_counts.per_class_backward && (
                          <div className="detail-subsection">
                            <h4>역방향 차종별</h4>
                            <div className="class-counts">
                              {Object.entries(selectedTask.vehicle_counts.per_class_backward).map(([vehicleType, count]) => (
                                <div key={vehicleType} className="class-count-item">
                                  <span className="class-name">{vehicleType}:</span>
                                  <span className="class-count">{count}대</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Line 정보 */}
                        {selectedTask.vehicle_counts.line_a && (
                          <div className="detail-row">
                            <span className="detail-label">Line A:</span>
                            <span className="detail-value">
                              [{selectedTask.vehicle_counts.line_a.join(', ')}]
                            </span>
                          </div>
                        )}
                        {selectedTask.vehicle_counts.line_b && (
                          <div className="detail-row">
                            <span className="detail-label">Line B:</span>
                            <span className="detail-value">
                              [{selectedTask.vehicle_counts.line_b.join(', ')}]
                            </span>
                          </div>
                        )}
                        {selectedTask.vehicle_counts.fps && (
                          <div className="detail-row">
                            <span className="detail-label">FPS:</span>
                            <span className="detail-value">{selectedTask.vehicle_counts.fps}</span>
                          </div>
                        )}
                        {selectedTask.vehicle_counts.frames_processed && (
                          <div className="detail-row">
                            <span className="detail-label">처리된 프레임:</span>
                            <span className="detail-value">{selectedTask.vehicle_counts.frames_processed}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Home;

