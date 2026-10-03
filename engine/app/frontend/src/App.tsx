import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './shared/Layout';
import { OverviewPage } from './pages/OverviewPage';
import { TalkWalkPage } from './pages/talkwalk/TalkWalkPage';
import { GreennessPage } from './pages/greenness/GreennessPage';
import { GmbPage } from './pages/GmbPage';
import { FirmPage } from './pages/firm/FirmPage';
import { MethodPage } from './pages/method/MethodPage';
import { PipelinePage } from './pages/pipeline/PipelinePage';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/talkwalk" element={<TalkWalkPage />} />
        <Route path="/greenness" element={<GreennessPage />} />
        <Route path="/gmb" element={<GmbPage />} />
        <Route path="/firms/:firmId" element={<FirmPage />} />
        <Route path="/method" element={<MethodPage />} />
        <Route path="/pipeline" element={<PipelinePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
