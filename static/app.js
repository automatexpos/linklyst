// basic drag reorder (HTML5) - when user finishes, we POST new order to /link/reorder
document.addEventListener('DOMContentLoaded', function(){
  const list = document.getElementById('links-list');
  if(!list) return;

  let dragEl = null;
  list.querySelectorAll('li').forEach(li=>{
    li.draggable = true;
    li.addEventListener('dragstart', (e)=> {
      dragEl = li;
      li.classList.add('dragging');
    });
    li.addEventListener('dragend', (e)=> {
      li.classList.remove('dragging');
      dragEl = null;
      // send order
      const ids = Array.from(list.querySelectorAll('li')).map(i => i.dataset.id).filter(Boolean);
      fetch('/link/reorder', {
        method:'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(ids)
      }).then(()=> console.log('order saved')).catch(()=>{});
    });
    li.addEventListener('dragover', (e)=> {
      e.preventDefault();
      const target = e.currentTarget;
      if(target === dragEl) return;
      const rect = target.getBoundingClientRect();
      const next = (e.clientY - rect.top) > rect.height/2;
      target.parentNode.insertBefore(dragEl, next? target.nextSibling : target);
    });
  });

  // Avatar file upload handling
  const fileInputs = document.querySelectorAll('input[type="file"]');
  fileInputs.forEach(input => {
    const helper = input.nextElementSibling;
    
    if (helper && helper.classList.contains('file-input-helper')) {
      helper.addEventListener('click', () => {
        input.click();
      });
      
      helper.addEventListener('dragover', (e) => {
        e.preventDefault();
        helper.style.borderColor = 'var(--primary)';
        helper.style.background = 'var(--bg-tertiary)';
      });
      
      helper.addEventListener('dragleave', () => {
        helper.style.borderColor = 'var(--border)';
        helper.style.background = 'var(--bg-primary)';
      });
      
      helper.addEventListener('drop', (e) => {
        e.preventDefault();
        helper.style.borderColor = 'var(--border)';
        helper.style.background = 'var(--bg-primary)';
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
          input.files = files;
          updateFileLabel(input, files[0].name);
        }
      });
      
      input.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
          updateFileLabel(input, e.target.files[0].name);
        }
      });
    }
  });
  
  function updateFileLabel(input, fileName) {
    const helper = input.nextElementSibling;
    const fileText = helper.querySelector('.file-text');
    if (fileText) {
      fileText.textContent = `Selected: ${fileName}`;
    }
  }

});
