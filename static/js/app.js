const { createApp, ref, reactive, computed, onMounted, watch } = Vue;

const API_BASE = '/api';

function getToken() {
    return localStorage.getItem('token') || '';
}

async function fetchApi(url, options = {}) {
    const token = getToken();
    const headers = { ...options.headers };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers
    });

    if (response.status === 401 && !options.skipAuthRedirect) {
        localStorage.removeItem('token');
        localStorage.removeItem('auth');
        window.location.reload();
        throw new Error('认证已过期');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: '请求失败' }));
        throw new Error(error.detail || '请求失败');
    }

    return response;
}

const app = createApp({
    setup() {
        const auth = reactive({
            token: localStorage.getItem('token') || '',
            user_type: localStorage.getItem('user_type') || '',
            username: localStorage.getItem('username') || '',
            project_uuid: localStorage.getItem('project_uuid') || '',
            user_id: parseInt(localStorage.getItem('user_id') || '0')
        });

        const loginType = ref('user');
        const loginForm = reactive({
            project_uuid: '',
            username: '',
            password: ''
        });

        const currentPage = ref('projects');
        const sidebarOpen = ref(false);

        const projects = ref([]);
        const selectedProject = ref(null);
        const projectUsers = ref([]);
        const projectImages = ref([]);
        const selectedImages = ref([]);
        const imagePagination = ref({ page: 1, total_pages: 0 });
        const pageSize = ref(50);

        const showCreateProject = ref(false);
        const newProjectName = ref('');

        const showCreateUser = ref(false);
        const newUser = reactive({ username: '', password: '' });

        const showPasswordModal = ref(false);
        const newPassword = ref('');
        const changingUser = ref(null);

        const uploading = ref(false);
        const uploadProgress = ref(0);

        const viewingImage = ref(null);

        const toasts = ref([]);
        let toastId = 0;

        const fileInput = ref(null);

        const faceRegisterName = ref('');
        const registeredFaces = ref([]);
        const faceSearchResults = ref([]);
        const faceSearchMatchCount = ref(0);
        const faceRegistering = ref(false);

        const projectRegisteredFaces = ref([]);
        const projectFaceSearchResults = ref([]);
        const projectFaceSearching = ref(false);
        const projectFaceSearchName = ref('');

        const sortOrder = ref('desc');
        const filterUploader = ref('');

        const filteredImages = computed(() => {
            let images = [...projectImages.value];
            if (filterUploader.value) {
                images = images.filter(img => img.uploader_name === filterUploader.value);
            }
            images.sort((a, b) => {
                const timeA = new Date(a.created_at).getTime();
                const timeB = new Date(b.created_at).getTime();
                return sortOrder.value === 'desc' ? timeB - timeA : timeA - timeB;
            });
            return images;
        });

        const uploaders = computed(() => {
            const names = [...new Set(projectImages.value.map(img => img.uploader_name))];
            return names.sort();
        });

        const pageTitle = computed(() => {
            const titles = {
                'admin-projects': '项目管理',
                'project-detail': selectedProject.value?.name || '项目详情',
                'projects': auth.project_uuid ? '项目图片' : '项目浏览',
                'face-manage': '人脸管理'
            };
            return titles[currentPage.value] || '';
        });

        function showToast(message, type = 'success') {
            const id = ++toastId;
            toasts.value.push({ id, message, type });
            setTimeout(() => {
                toasts.value = toasts.value.filter(t => t.id !== id);
            }, 3000);
        }

        function formatDate(dateStr) {
            if (!dateStr) return '';
            const date = new Date(dateStr);
            return date.toLocaleString('zh-CN');
        }

        function formatSize(bytes) {
            if (!bytes) return '0 B';
            const units = ['B', 'KB', 'MB', 'GB'];
            let i = 0;
            while (bytes >= 1024 && i < units.length - 1) {
                bytes /= 1024;
                i++;
            }
            return bytes.toFixed(1) + ' ' + units[i];
        }

        async function adminLogin() {
            try {
                const response = await fetchApi('/auth/admin/login', {
                    method: 'POST',
                    skipAuthRedirect: true,
                    body: JSON.stringify({
                        username: loginForm.username,
                        password: loginForm.password
                    })
                });
                const data = await response.json();

                localStorage.setItem('token', data.token);
                localStorage.setItem('user_type', data.user_type);
                localStorage.setItem('username', data.username);
                localStorage.setItem('project_uuid', '');

                auth.token = data.token;
                auth.user_type = data.user_type;
                auth.username = data.username;
                auth.project_uuid = '';

                currentPage.value = 'admin-projects';
                loadProjects();
                showToast('登录成功');
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        async function userLogin() {
            try {
                const response = await fetchApi('/auth/user/login', {
                    method: 'POST',
                    skipAuthRedirect: true,
                    body: JSON.stringify(loginForm)
                });
                const data = await response.json();

                localStorage.setItem('token', data.token);
                localStorage.setItem('user_type', data.user_type);
                localStorage.setItem('username', data.username);
                localStorage.setItem('project_uuid', data.project_uuid);

                auth.token = data.token;
                auth.user_type = data.user_type;
                auth.username = data.username;
                auth.project_uuid = data.project_uuid;

                const meResp = await fetchApi('/auth/me');
                const meData = await meResp.json();
                auth.user_id = meData.id;
                localStorage.setItem('user_id', meData.id.toString());

                currentPage.value = 'projects';
                loadProjectImages(data.project_uuid);
                showToast('登录成功');
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        function logout() {
            auth.token = '';
            auth.user_type = '';
            auth.username = '';
            auth.project_uuid = '';
            auth.user_id = 0;
            localStorage.clear();
        }

        function navigateTo(page) {
            currentPage.value = page;
            sidebarOpen.value = false;
            selectedImages.value = [];
            projectFaceSearchResults.value = [];
            projectFaceSearchName.value = '';

            if (page === 'admin-projects') {
                loadProjects();
            } else if (page === 'projects') {
                if (auth.user_type === 'admin') {
                    loadProjects();
                } else if (auth.project_uuid) {
                    loadProjectImages(auth.project_uuid);
                }
                loadProjectRegisteredFaces();
            } else if (page === 'face-manage') {
                loadRegisteredFaces();
            }
        }

        async function loadProjects() {
            try {
                const response = await fetchApi('/projects');
                projects.value = await response.json();
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        async function selectProject(project) {
            selectedProject.value = project;
            currentPage.value = 'project-detail';
            projectFaceSearchResults.value = [];
            projectFaceSearchName.value = '';
            await loadProjectUsers(project.uuid);
            await loadProjectImages(project.uuid);
            await loadProjectRegisteredFaces();
        }

        async function enterProject(project) {
            auth.project_uuid = project.uuid;
            localStorage.setItem('project_uuid', project.uuid);
            await loadProjectImages(project.uuid);
            await loadProjectRegisteredFaces();
        }

        async function loadProjectUsers(uuid) {
            try {
                const response = await fetchApi(`/projects/${uuid}/users`);
                projectUsers.value = await response.json();
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        async function loadProjectImages(uuid, page = 1) {
            try {
                const targetUuid = uuid || auth.project_uuid || selectedProject.value?.uuid;
                if (!targetUuid) return;

                const response = await fetchApi(`/projects/${targetUuid}/images?page=${page}&page_size=${pageSize.value}`);
                const data = await response.json();
                projectImages.value = data.items;
                imagePagination.value = {
                    page: data.page,
                    total_pages: data.total_pages
                };
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        async function loadImages(page) {
            await loadProjectImages(null, page);
        }

        function changePageSize(size) {
            pageSize.value = size;
            loadProjectImages(null, 1);
        }

        async function createProject() {
            if (!newProjectName.value.trim()) {
                showToast('请输入项目名称', 'error');
                return;
            }
            try {
                await fetchApi('/projects', {
                    method: 'POST',
                    body: JSON.stringify({ name: newProjectName.value })
                });
                showCreateProject.value = false;
                newProjectName.value = '';
                await loadProjects();
                showToast('创建成功');
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        async function deleteProject() {
            if (!confirm('确定删除此项目？所有图片和用户将被永久删除！')) return;
            try {
                await fetchApi(`/projects/${selectedProject.value.uuid}`, { method: 'DELETE' });
                navigateTo('admin-projects');
                showToast('删除成功');
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        function copyUuid() {
            navigator.clipboard.writeText(selectedProject.value.uuid);
            showToast('已复制项目ID');
        }

        async function createUser() {
            try {
                const response = await fetchApi(`/projects/${selectedProject.value.uuid}/users`, {
                    method: 'POST',
                    body: JSON.stringify(newUser)
                });
                const data = await response.json();
                showCreateUser.value = false;
                newUser.username = '';
                newUser.password = '';
                await loadProjectUsers(selectedProject.value.uuid);
                showToast(`用户创建成功\n用户名: ${data.username}\n密码: ${data.password}`);
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        function showChangePassword(user) {
            changingUser.value = user;
            newPassword.value = '';
            showPasswordModal.value = true;
        }

        async function changePassword() {
            if (!newPassword.value) {
                showToast('请输入新密码', 'error');
                return;
            }
            try {
                await fetchApi(`/projects/${selectedProject.value.uuid}/users/${changingUser.value.id}/password`, {
                    method: 'PUT',
                    body: JSON.stringify({ new_password: newPassword.value })
                });
                showPasswordModal.value = false;
                showToast('密码修改成功');
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        async function deleteUser(user) {
            if (!confirm(`确定删除用户 ${user.username}？`)) return;
            try {
                await fetchApi(`/projects/${selectedProject.value.uuid}/users/${user.id}`, { method: 'DELETE' });
                await loadProjectUsers(selectedProject.value.uuid);
                showToast('删除成功');
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        function triggerUpload() {
            fileInput.value?.click();
        }

        async function handleFileSelect(event) {
            const files = event.target.files;
            if (files.length > 0) {
                await uploadFiles(files);
            }
            event.target.value = '';
        }

        async function handleDrop(event) {
            event.target.classList.remove('dragover');
            const files = event.dataTransfer.files;
            if (files.length > 0) {
                await uploadFiles(files);
            }
        }

        async function uploadFiles(files) {
            const uuid = selectedProject.value?.uuid || auth.project_uuid;
            if (!uuid) {
                showToast('请先选择项目', 'error');
                return;
            }

            uploading.value = true;
            uploadProgress.value = 0;

            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }

            try {
                const xhr = new XMLHttpRequest();
                xhr.open('POST', `${API_BASE}/projects/${uuid}/images`);
                xhr.setRequestHeader('Authorization', `Bearer ${auth.token}`);

                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        uploadProgress.value = Math.round((e.loaded / e.total) * 100);
                    }
                });

                await new Promise((resolve, reject) => {
                    xhr.onload = () => {
                        if (xhr.status >= 200 && xhr.status < 300) {
                            const data = JSON.parse(xhr.responseText);
                            showToast(`上传成功 ${data.success} 张${data.failed > 0 ? `，失败 ${data.failed} 张` : ''}`);
                            loadProjectImages(uuid);
                            resolve();
                        } else {
                            reject(new Error('上传失败'));
                        }
                    };
                    xhr.onerror = () => reject(new Error('上传失败'));
                    xhr.send(formData);
                });
            } catch (e) {
                showToast(e.message, 'error');
            } finally {
                uploading.value = false;
                uploadProgress.value = 0;
            }
        }

        async function downloadImage(image) {
            const uuid = selectedProject.value?.uuid || auth.project_uuid;
            const link = document.createElement('a');
            link.href = `${API_BASE}/projects/${uuid}/images/${image.id}/download`;
            link.setAttribute('download', image.original_name);

            const token = getToken();
            try {
                const response = await fetch(link.href, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                link.href = url;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            } catch (e) {
                showToast('下载失败', 'error');
            }
        }

        async function batchDownload() {
            if (selectedImages.value.length === 0) return;

            const uuid = selectedProject.value?.uuid || auth.project_uuid;

            try {
                const response = await fetchApi(`/projects/${uuid}/images/batch-download`, {
                    method: 'POST',
                    body: JSON.stringify(selectedImages.value)
                });

                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `images_${new Date().getTime()}.zip`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);

                selectedImages.value = [];
                showToast('下载成功');
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        async function deleteImage(image) {
            if (!confirm(`确定删除 ${image.original_name}？`)) return;

            const uuid = selectedProject.value?.uuid || auth.project_uuid;
            try {
                await fetchApi(`/projects/${uuid}/images/${image.id}`, { method: 'DELETE' });
                await loadProjectImages(uuid);
                showToast('删除成功');
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        async function batchDelete() {
            if (selectedImages.value.length === 0) return;
            if (!confirm(`确定删除选中的 ${selectedImages.value.length} 张图片？`)) return;

            const uuid = selectedProject.value?.uuid || auth.project_uuid;
            let success = 0;
            let failed = 0;

            for (const id of selectedImages.value) {
                try {
                    await fetchApi(`/projects/${uuid}/images/${id}`, { method: 'DELETE' });
                    success++;
                } catch (e) {
                    failed++;
                }
            }

            selectedImages.value = [];
            await loadProjectImages(uuid);
            showToast(`删除完成: 成功 ${success}，失败 ${failed}`);
        }

        function viewImage(image) {
            viewingImage.value = image;
        }

        async function loadRegisteredFaces() {
            try {
                const response = await fetchApi('/face/list');
                const data = await response.json();
                registeredFaces.value = data.names;
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        async function handleFaceRegister(event) {
            const files = event.target.files;
            if (!files.length) return;
            if (!faceRegisterName.value.trim()) {
                showToast('请输入姓名', 'error');
                event.target.value = '';
                return;
            }

            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }

            faceRegistering.value = true;
            try {
                const response = await fetch(`/api/face/register?name=${encodeURIComponent(faceRegisterName.value.trim())}`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${auth.token}` },
                    body: formData
                });
                const data = await response.json();
                if (response.ok) {
                    showToast(data.message);
                    faceRegisterName.value = '';
                    await loadRegisteredFaces();
                } else {
                    showToast(data.detail || '注册失败', 'error');
                }
            } catch (e) {
                showToast('注册失败', 'error');
            } finally {
                faceRegistering.value = false;
            }
            event.target.value = '';
        }

        async function deleteFace(name) {
            if (!confirm(`确定删除 ${name} 的人脸数据？`)) return;
            try {
                await fetchApi(`/face/delete/${encodeURIComponent(name)}`, { method: 'DELETE' });
                await loadRegisteredFaces();
                showToast('删除成功');
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        async function handleFaceSearch(event) {
            const files = event.target.files;
            if (!files.length) return;

            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }

            try {
                showToast('正在检索，请稍候...', 'warning');
                const response = await fetch('/api/face/search', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${auth.token}` },
                    body: formData
                });
                const data = await response.json();
                if (response.ok) {
                    faceSearchResults.value = data.results;
                    faceSearchMatchCount.value = data.matched_count;
                    showToast(`检索完成，${data.matched_count} 张匹配`);
                } else {
                    showToast(data.detail || '检索失败', 'error');
                }
            } catch (e) {
                showToast('检索失败', 'error');
            }
            event.target.value = '';
        }

        async function loadProjectRegisteredFaces() {
            try {
                const response = await fetchApi('/face/list');
                const data = await response.json();
                projectRegisteredFaces.value = data.names;
            } catch (e) {
                projectRegisteredFaces.value = [];
            }
        }

        async function searchProjectFace(name) {
            const uuid = selectedProject.value?.uuid || auth.project_uuid;
            if (!uuid) return;

            projectFaceSearching.value = true;
            projectFaceSearchName.value = name;
            try {
                showToast('正在检索人脸，请稍候...', 'warning');
                const response = await fetchApi(`/face/search-in-project/${uuid}?name=${encodeURIComponent(name)}`);
                const data = await response.json();
                projectFaceSearchResults.value = data.results;
                showToast(`检索完成，${data.matched_count} 张匹配`);
            } catch (e) {
                showToast(e.message, 'error');
                projectFaceSearchResults.value = [];
            } finally {
                projectFaceSearching.value = false;
            }
        }

        function clearProjectFaceSearch() {
            projectFaceSearchResults.value = [];
            projectFaceSearchName.value = '';
        }

        onMounted(() => {
            if (auth.token) {
                if (auth.user_type === 'admin') {
                    currentPage.value = 'admin-projects';
                    loadProjects();
                } else if (auth.project_uuid) {
                    currentPage.value = 'projects';
                    loadProjectImages(auth.project_uuid);
                }
            }
        });

        return {
            auth,
            loginType,
            loginForm,
            currentPage,
            sidebarOpen,
            projects,
            selectedProject,
            projectUsers,
            projectImages,
            selectedImages,
            imagePagination,
            pageSize,
            showCreateProject,
            newProjectName,
            showCreateUser,
            newUser,
            showPasswordModal,
            newPassword,
            changingUser,
            uploading,
            uploadProgress,
            viewingImage,
            toasts,
            fileInput,
            pageTitle,
            showToast,
            formatDate,
            formatSize,
            adminLogin,
            userLogin,
            logout,
            navigateTo,
            loadProjects,
            selectProject,
            enterProject,
            loadProjectUsers,
            loadProjectImages,
            loadImages,
            changePageSize,
            createProject,
            deleteProject,
            copyUuid,
            createUser,
            showChangePassword,
            changePassword,
            deleteUser,
            triggerUpload,
            handleFileSelect,
            handleDrop,
            uploadFiles,
            downloadImage,
            batchDownload,
            deleteImage,
            batchDelete,
            viewImage,
            faceRegisterName,
            registeredFaces,
            faceSearchResults,
            faceSearchMatchCount,
            faceRegistering,
            loadRegisteredFaces,
            handleFaceRegister,
            deleteFace,
            handleFaceSearch,
            projectRegisteredFaces,
            projectFaceSearchResults,
            projectFaceSearching,
            projectFaceSearchName,
            sortOrder,
            filterUploader,
            filteredImages,
            uploaders,
            loadProjectRegisteredFaces,
            searchProjectFace,
            clearProjectFaceSearch
        };
    }
});

app.mount('#app');
