import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Login.css';

function Login() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    userId: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // 기본 유효성 검사
    if (!formData.userId || !formData.password) {
      setError('아이디와 비밀번호를 모두 입력해주세요.');
      return;
    }

    setIsLoading(true);

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('user_id', formData.userId);
      formDataToSend.append('password', formData.password);

      const response = await fetch('http://localhost:5000/auth/login', {
        method: 'POST',
        body: formDataToSend,
      });

      const data = await response.json();

      if (!response.ok) {
        // 에러 응답 처리
        setError(data.message || '로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.');
        setIsLoading(false);
        return;
      }

      // 로그인 성공
      console.log('Login successful:', data);
      
      // 토큰이 있다면 localStorage에 저장
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
      }
      
      // 사용자 정보가 있다면 저장
      if (data.user) {
        localStorage.setItem('user', JSON.stringify(data.user));
      }

      // 로그인 성공 후 Home으로 이동
      navigate('/home', { replace: true });

    } catch (err) {
      console.error('Login error:', err);
      setError('서버에 연결할 수 없습니다. 나중에 다시 시도해주세요.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>로그인</h1>
          <p>계정에 로그인하세요</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="userId">아이디</label>
            <input
              type="text"
              id="userId"
              name="userId"
              value={formData.userId}
              onChange={handleChange}
              placeholder="아이디를 입력하세요"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">비밀번호</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="비밀번호를 입력하세요"
              required
            />
          </div>

          <div className="form-options">
            <label className="checkbox-label">
              <input type="checkbox" />
              <span>로그인 상태 유지</span>
            </label>
            <a href="#" className="forgot-password">비밀번호 찾기</a>
          </div>

          <button type="submit" className="login-button" disabled={isLoading}>
            {isLoading ? '로그인 중...' : '로그인'}
          </button>
        </form>

        <div className="login-footer">
          <p>
            계정이 없으신가요? <a href="#">회원가입</a>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;

