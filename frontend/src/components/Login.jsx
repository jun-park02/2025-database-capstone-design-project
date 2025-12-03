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
  const [isForgotPasswordOpen, setIsForgotPasswordOpen] = useState(false);
  const [forgotPasswordData, setForgotPasswordData] = useState({
    userId: '',
    email: '',
    newPassword: '',
    newPasswordConfirm: '',
  });
  const [forgotPasswordError, setForgotPasswordError] = useState('');
  const [forgotPasswordSuccess, setForgotPasswordSuccess] = useState(false);
  const [isForgotPasswordLoading, setIsForgotPasswordLoading] = useState(false);

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
            <a 
              href="#" 
              className="forgot-password"
              onClick={(e) => {
                e.preventDefault();
                setIsForgotPasswordOpen(true);
              }}
            >
              비밀번호 찾기
            </a>
          </div>

          <button type="submit" className="login-button" disabled={isLoading}>
            {isLoading ? '로그인 중...' : '로그인'}
          </button>
        </form>

        <div className="login-footer">
          <p>
            계정이 없으신가요? <a href="#" onClick={(e) => { e.preventDefault(); navigate('/signup'); }}>회원가입</a>
          </p>
        </div>
      </div>

      {/* 비밀번호 찾기 모달 */}
      {isForgotPasswordOpen && (
        <div className="modal-overlay" onClick={() => {
          setIsForgotPasswordOpen(false);
          setForgotPasswordData({ userId: '', email: '', newPassword: '', newPasswordConfirm: '' });
          setForgotPasswordError('');
          setForgotPasswordSuccess(false);
        }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>비밀번호 찾기</h2>
              <button 
                className="modal-close-button" 
                onClick={() => {
                  setIsForgotPasswordOpen(false);
                  setForgotPasswordData({ userId: '', email: '', newPassword: '', newPasswordConfirm: '' });
                  setForgotPasswordError('');
                  setForgotPasswordSuccess(false);
                }}
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              {forgotPasswordSuccess ? (
                <div className="success-message">
                  <p>비밀번호가 성공적으로 재설정되었습니다.</p>
                  <p>새 비밀번호로 로그인해주세요.</p>
                </div>
              ) : (
                <form 
                  onSubmit={async (e) => {
                    e.preventDefault();
                    setForgotPasswordError('');

                    if (!forgotPasswordData.userId || !forgotPasswordData.email || !forgotPasswordData.newPassword || !forgotPasswordData.newPasswordConfirm) {
                      setForgotPasswordError('모든 필수 정보를 입력해주세요.');
                      return;
                    }

                    if (forgotPasswordData.newPassword.length < 6) {
                      setForgotPasswordError('새 비밀번호는 최소 6자 이상이어야 합니다.');
                      return;
                    }

                    if (forgotPasswordData.newPassword !== forgotPasswordData.newPasswordConfirm) {
                      setForgotPasswordError('새 비밀번호가 일치하지 않습니다.');
                      return;
                    }

                    setIsForgotPasswordLoading(true);

                    try {
                      const formDataToSend = new FormData();
                      formDataToSend.append('user_id', forgotPasswordData.userId);
                      formDataToSend.append('user_email', forgotPasswordData.email);
                      formDataToSend.append('new_password', forgotPasswordData.newPassword);

                      const response = await fetch('http://localhost:5000/users/password/reset', {
                        method: 'PUT',
                        body: formDataToSend,
                      });

                      const data = await response.json();

                      if (!response.ok) {
                        setForgotPasswordError(data.message || '비밀번호 찾기에 실패했습니다. 아이디와 이메일을 확인해주세요.');
                        setIsForgotPasswordLoading(false);
                        return;
                      }

                      // 성공
                      setForgotPasswordSuccess(true);
                      setIsForgotPasswordLoading(false);
                    } catch (err) {
                      console.error('Forgot password error:', err);
                      setForgotPasswordError('서버에 연결할 수 없습니다. 나중에 다시 시도해주세요.');
                      setIsForgotPasswordLoading(false);
                    }
                  }}
                  className="forgot-password-form"
                >
                  {forgotPasswordError && (
                    <div className="error-message">{forgotPasswordError}</div>
                  )}

                  <div className="form-group">
                    <label htmlFor="forgotUserId">아이디</label>
                    <input
                      type="text"
                      id="forgotUserId"
                      name="userId"
                      value={forgotPasswordData.userId}
                      onChange={(e) => {
                        setForgotPasswordData(prev => ({
                          ...prev,
                          userId: e.target.value,
                        }));
                        setForgotPasswordError('');
                      }}
                      placeholder="아이디를 입력하세요"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="forgotEmail">이메일</label>
                    <input
                      type="email"
                      id="forgotEmail"
                      name="email"
                      value={forgotPasswordData.email}
                      onChange={(e) => {
                        setForgotPasswordData(prev => ({
                          ...prev,
                          email: e.target.value,
                        }));
                        setForgotPasswordError('');
                      }}
                      placeholder="이메일을 입력하세요"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="newPassword">새 비밀번호</label>
                    <input
                      type="password"
                      id="newPassword"
                      name="newPassword"
                      value={forgotPasswordData.newPassword}
                      onChange={(e) => {
                        setForgotPasswordData(prev => ({
                          ...prev,
                          newPassword: e.target.value,
                        }));
                        setForgotPasswordError('');
                      }}
                      placeholder="새 비밀번호를 입력하세요 (최소 6자)"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="newPasswordConfirm">새 비밀번호 확인</label>
                    <input
                      type="password"
                      id="newPasswordConfirm"
                      name="newPasswordConfirm"
                      value={forgotPasswordData.newPasswordConfirm}
                      onChange={(e) => {
                        setForgotPasswordData(prev => ({
                          ...prev,
                          newPasswordConfirm: e.target.value,
                        }));
                        setForgotPasswordError('');
                      }}
                      placeholder="새 비밀번호를 다시 입력하세요"
                      required
                    />
                  </div>

                  <button 
                    type="submit" 
                    className="forgot-password-button" 
                    disabled={isForgotPasswordLoading}
                  >
                    {isForgotPasswordLoading ? '재설정 중...' : '비밀번호 재설정'}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Login;

