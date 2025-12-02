import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import './TrafficStats.css';

function TrafficStats() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [filters, setFilters] = useState({
    region: '',
    date: '',
    time: '',
  });
  const [trafficData, setTrafficData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [regions, setRegions] = useState([]);

  useEffect(() => {
    // localStorage에서 사용자 정보 가져오기
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    }
    // 사용 가능한 지역 목록 가져오기
    fetchRegions();
  }, []);

  const fetchRegions = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5000/video/regions', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.regions && Array.isArray(data.regions)) {
          setRegions(data.regions);
        }
      }
    } catch (err) {
      console.error('Fetch regions error:', err);
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value,
    }));
    setError('');
  };

  const handleSearch = async () => {
    if (!filters.region && !filters.date && !filters.time) {
      setError('최소 하나의 필터 조건을 선택해주세요.');
      return;
    }

    setIsLoading(true);
    setError('');
    setTrafficData([]);

    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      
      if (filters.region) params.append('region', filters.region);
      if (filters.date) params.append('date', filters.date);
      if (filters.time) params.append('time', filters.time);

      const response = await fetch(`http://localhost:5000/video/statistics?${params.toString()}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.message || '통행량 데이터를 불러오는데 실패했습니다.');
        setIsLoading(false);
        return;
      }

      // API 응답 형식에 따라 데이터 설정
      if (data.statistics) {
        setTrafficData(Array.isArray(data.statistics) ? data.statistics : [data.statistics]);
      } else if (Array.isArray(data)) {
        setTrafficData(data);
      } else {
        setTrafficData([]);
      }
      setIsLoading(false);
    } catch (err) {
      console.error('Fetch traffic stats error:', err);
      setError('서버에 연결할 수 없습니다. 나중에 다시 시도해주세요.');
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setFilters({
      region: '',
      date: '',
      time: '',
    });
    setTrafficData([]);
    setError('');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login', { replace: true });
  };

  const formatDateTime = (dateTimeStr) => {
    if (!dateTimeStr) return 'N/A';
    try {
      const date = new Date(dateTimeStr);
      return date.toLocaleString('ko-KR');
    } catch {
      return dateTimeStr;
    }
  };

  // 전체 합계 계산
  const totalSummary = useMemo(() => {
    let totalForward = 0;
    let totalBackward = 0;

    trafficData.forEach((item) => {
      if (item.vehicle_counts) {
        totalForward += item.vehicle_counts.total_forward || 0;
        totalBackward += item.vehicle_counts.total_backward || 0;
      } else {
        totalForward += item.total_forward || 0;
        totalBackward += item.total_backward || 0;
      }
    });

    return {
      totalForward,
      totalBackward,
      total: totalForward + totalBackward,
    };
  }, [trafficData]);

  return (
    <div className="traffic-stats-container">
      <header className="traffic-stats-header">
        <div className="header-content">
          <h1>자동차 통행량 조회</h1>
          <div className="user-info">
            {user && (
              <span className="welcome-text">
                환영합니다, {user.user_id || user.name || '사용자'}님!
              </span>
            )}
            <button onClick={() => navigate('/home')} className="home-button">
              홈으로
            </button>
            <button onClick={handleLogout} className="logout-button">
              로그아웃
            </button>
          </div>
        </div>
      </header>

      <main className="traffic-stats-main">
        <div className="traffic-stats-content">
          {/* 필터 섹션 */}
          <div className="filter-card">
            <h2>조회 조건</h2>
            <div className="filter-form">
              <div className="filter-group">
                <label htmlFor="region">지역</label>
                <input
                  type="text"
                  id="region"
                  name="region"
                  value={filters.region}
                  onChange={handleFilterChange}
                  placeholder="지역을 입력하세요 (예: 서울시 강남구)"
                  list="region-list"
                />
                {regions.length > 0 && (
                  <datalist id="region-list">
                    {regions.map((region, index) => (
                      <option key={index} value={region} />
                    ))}
                  </datalist>
                )}
              </div>

              <div className="filter-group">
                <label htmlFor="date">날짜</label>
                <input
                  type="date"
                  id="date"
                  name="date"
                  value={filters.date}
                  onChange={handleFilterChange}
                />
              </div>

              <div className="filter-group">
                <label htmlFor="time">시간</label>
                <input
                  type="time"
                  id="time"
                  name="time"
                  value={filters.time}
                  onChange={handleFilterChange}
                />
              </div>

              <div className="filter-actions">
                <button 
                  onClick={handleSearch} 
                  className="search-button"
                  disabled={isLoading}
                >
                  {isLoading ? '조회 중...' : '조회'}
                </button>
                <button 
                  onClick={handleReset} 
                  className="reset-button"
                  disabled={isLoading}
                >
                  초기화
                </button>
              </div>
            </div>

            {error && <div className="error-message">{error}</div>}
          </div>

          {/* 결과 섹션 */}
          <div className="results-card">
            <h2>조회 결과</h2>
            {isLoading ? (
              <div className="loading-message">데이터를 불러오는 중...</div>
            ) : trafficData.length === 0 ? (
              <div className="empty-message">
                {filters.region || filters.date || filters.time 
                  ? '조회 조건에 맞는 데이터가 없습니다.' 
                  : '조회 조건을 선택하고 조회 버튼을 눌러주세요.'}
              </div>
            ) : (
              <>
                {/* 전체 합계 */}
                <div className="total-summary-card">
                  <h3>전체 합계</h3>
                  <div className="total-summary-grid">
                    <div className="total-summary-item">
                      <span className="total-summary-label">총 정방향:</span>
                      <span className="total-summary-value highlight">
                        {totalSummary.totalForward.toLocaleString()}대
                      </span>
                    </div>
                    <div className="total-summary-item">
                      <span className="total-summary-label">총 역방향:</span>
                      <span className="total-summary-value highlight">
                        {totalSummary.totalBackward.toLocaleString()}대
                      </span>
                    </div>
                    <div className="total-summary-item total">
                      <span className="total-summary-label">전체 합계:</span>
                      <span className="total-summary-value highlight total">
                        {totalSummary.total.toLocaleString()}대
                      </span>
                    </div>
                  </div>
                  <div className="total-summary-count">
                    조회된 데이터: {trafficData.length}건
                  </div>
                </div>

                <div className="traffic-data-list">
                {trafficData.map((item, index) => (
                  <div key={index} className="traffic-data-item">
                    <div className="data-header">
                      <h3>통행량 데이터 #{index + 1}</h3>
                      {item.video_id && (
                        <span className="video-id">Video ID: {item.video_id}</span>
                      )}
                    </div>

                    <div className="data-content">
                      <div className="data-section">
                        <h4>기본 정보</h4>
                        <div className="data-grid">
                          {item.region && (
                            <div className="data-row">
                              <span className="data-label">지역:</span>
                              <span className="data-value">{item.region}</span>
                            </div>
                          )}
                          {item.recorded_at && (
                            <div className="data-row">
                              <span className="data-label">촬영 일시:</span>
                              <span className="data-value">{formatDateTime(item.recorded_at)}</span>
                            </div>
                          )}
                          {item.counted_at && (
                            <div className="data-row">
                              <span className="data-label">집계 일시:</span>
                              <span className="data-value">{formatDateTime(item.counted_at)}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {item.vehicle_counts && (
                        <div className="data-section">
                          <h4>차량 통계</h4>
                          <div className="data-grid">
                            <div className="data-row">
                              <span className="data-label">총 정방향:</span>
                              <span className="data-value highlight">
                                {item.vehicle_counts.total_forward || 0}대
                              </span>
                            </div>
                            <div className="data-row">
                              <span className="data-label">총 역방향:</span>
                              <span className="data-value highlight">
                                {item.vehicle_counts.total_backward || 0}대
                              </span>
                            </div>
                            <div className="data-row">
                              <span className="data-label">합계:</span>
                              <span className="data-value highlight total">
                                {(item.vehicle_counts.total_forward || 0) + (item.vehicle_counts.total_backward || 0)}대
                              </span>
                            </div>

                            {item.vehicle_counts.per_class_forward && (
                              <div className="data-subsection">
                                <h5>정방향 차종별</h5>
                                <div className="class-counts">
                                  {Object.entries(item.vehicle_counts.per_class_forward).map(([vehicleType, count]) => (
                                    <div key={vehicleType} className="class-count-item">
                                      <span className="class-name">{vehicleType}:</span>
                                      <span className="class-count">{count}대</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {item.vehicle_counts.per_class_backward && (
                              <div className="data-subsection">
                                <h5>역방향 차종별</h5>
                                <div className="class-counts">
                                  {Object.entries(item.vehicle_counts.per_class_backward).map(([vehicleType, count]) => (
                                    <div key={vehicleType} className="class-count-item">
                                      <span className="class-name">{vehicleType}:</span>
                                      <span className="class-count">{count}대</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* 직접 vehicle_counts가 있는 경우 */}
                      {!item.vehicle_counts && (item.total_forward !== undefined || item.total_backward !== undefined) && (
                        <div className="data-section">
                          <h4>차량 통계</h4>
                          <div className="data-grid">
                            <div className="data-row">
                              <span className="data-label">총 정방향:</span>
                              <span className="data-value highlight">
                                {item.total_forward || 0}대
                              </span>
                            </div>
                            <div className="data-row">
                              <span className="data-label">총 역방향:</span>
                              <span className="data-value highlight">
                                {item.total_backward || 0}대
                              </span>
                            </div>
                            <div className="data-row">
                              <span className="data-label">합계:</span>
                              <span className="data-value highlight total">
                                {(item.total_forward || 0) + (item.total_backward || 0)}대
                              </span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                </div>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default TrafficStats;

