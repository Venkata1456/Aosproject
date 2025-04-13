// Function to create a folder
function createFolder() {
    const folderName = prompt("Enter the name of the new folder:");
    if (folderName) {
        fetch('/create_folder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ folderName: folderName })
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            listFolders(); // Refresh folder list
        })
        .catch(error => console.error('Error:', error));
    }
}

// Function to rename a folder
function renameFolder() {
    const oldFolderName = prompt("Enter the name of the folder to rename:");
    const newFolderName = prompt("Enter the new name for the folder:");
    if (oldFolderName && newFolderName) {
        fetch('/rename_folder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ oldFolderName: oldFolderName, newFolderName: newFolderName })
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            listFolders(); // Refresh folder list
        })
        .catch(error => console.error('Error:', error));
    }
}

// Function to delete a folder
function deleteFolder() {
    const folderName = prompt("Enter the name of the folder to delete:");
    if (folderName) {
        fetch('/delete_folder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ folderName: folderName })
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            listFolders(); // Refresh folder list
        })
        .catch(error => console.error('Error:', error));
    }
}

// Function to list all folders
function listFolders() {
    fetch('/list_folders')
    .then(response => response.json())
    .then(data => {
        const folderList = document.getElementById('folderList');
        folderList.innerHTML = '';
        data.folders.forEach(folder => {
            const folderItem = document.createElement('p');
            folderItem.textContent = folder;
            folderList.appendChild(folderItem);
        });
    })
    .catch(error => console.error('Error:', error));
}

// Function to list files
async function listFiles() {
    try {
        const response = await fetch('/list_files');
        let files = await response.json();
        files = files['files'];
        
        console.log('Files:', files);  // Log to confirm the data type
        
        if (!Array.isArray(files)) {
            alert('Error: Expected a list of files.');
            return;
        }

        const fileList = document.getElementById('fileList');
        const writeAccess = fileList.hasAttribute('allowChanges');
        fileList.innerHTML = '';

        files.forEach(file => {
            const fileElement = document.createElement('div');
            if (writeAccess) {
                fileElement.innerHTML = `
                    <span>${file}</span>
                    <button onclick="downloadFile('${file}')">Download</button>
                    <button onclick="deleteFile('${file}')">Delete</button>
                `;
            } else {
                fileElement.innerHTML = `
                    <span>${file}</span>
                `;
            }
            fileList.appendChild(fileElement);
        });
    } catch (error) {
        console.error('Error fetching files:', error);
        alert('Failed to load file list.');
    }
}


// Function to download a file
function downloadFile(filename) {
    window.location.href = `/download_file?filename=${encodeURIComponent(filename)}`;
}

// Function to delete a file
async function deleteFile(filename) {
    const confirmed = confirm(`Are you sure you want to delete ${filename}?`);
    if (confirmed) {
        const response = await fetch(`/delete_file?filename=${encodeURIComponent(filename)}`, { method: 'DELETE' });
        const result = await response.json();
        alert(result.message);
        listFiles(); // Refresh the file list
    }
}

function updateAccess(username, accessType, isChecked) {
    const formData = new FormData();
    formData.append('username', username);

    if (accessType === 'read') {
        formData.append('read_access', isChecked);
    } else if (accessType === 'write') {
        formData.append('write_access', isChecked);
    }

    fetch('/update_access', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
        } else {
            alert('Failed to update access');
        }
    })
    .catch(error => console.error('Error:', error));
}

function applyChanges(username) {
    // Get the read and write access values from the form
    const readAccess = document.getElementById('readAccess_' + username).checked;
    const writeAccess = document.getElementById('writeAccess_' + username).checked;

    // Create a new FormData object to send the data to the server
    const formData = new FormData();
    formData.append('username', username);
    formData.append('read_access', readAccess);
    formData.append('write_access', writeAccess);

    // Send the data to the server via a POST request
    fetch('/apply_changes', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        location.reload(); // Reload the page to show updated permissions
    })
    .catch(error => console.error('Error:', error));
}


