## 使用方法

启动后端:
./activate-backend.sh
uvicorn app.__main__:app --reload

启动前端:
./activate-frontend.sh
npm run dev

或手动激活:
### 后端
conda activate patent-backend
cd server
uvicorn app.__main__:app --reload

#### 前端
conda activate patent-frontend
cd client
npm run dev

环境已配置完成，可以开始开发了！