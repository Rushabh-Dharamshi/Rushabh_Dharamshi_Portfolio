const { Worker } = require('worker_threads');

class WorkerPool {
  constructor(workerPath, size) {
    this.workerPath = workerPath;
    this.size = Math.max(1, size);
    this.queue = [];
    this.workers = [];
    this.isClosing = false;

    for (let index = 0; index < this.size; index += 1) {
      this.workers.push(this.createWorker());
    }
  }

  createWorker() {
    const worker = new Worker(this.workerPath);
    const slot = { worker, busy: false, currentTask: null };

    worker.on('message', (message) => {
      if (!slot.currentTask) {
        return;
      }

      const { resolve, reject } = slot.currentTask;
      slot.currentTask = null;
      slot.busy = false;

      if (message.ok) {
        resolve(message.result);
      } else {
        reject(new Error(message.error || 'Worker execution failed'));
      }

      this.dispatch();
    });

    worker.on('error', (error) => {
      if (slot.currentTask) {
        slot.currentTask.reject(error);
        slot.currentTask = null;
      }

      slot.busy = false;
      if (!this.isClosing) {
        this.replaceWorker(slot);
        this.dispatch();
      }
    });

    worker.on('exit', (code) => {
      if (!this.isClosing && code !== 0) {
        this.replaceWorker(slot);
      }
    });

    return slot;
  }

  replaceWorker(slot) {
    const index = this.workers.indexOf(slot);
    if (index === -1) {
      return;
    }

    this.workers[index] = this.createWorker();
  }

  run(payload) {
    if (this.isClosing) {
      return Promise.reject(new Error('Worker pool is shutting down'));
    }

    return new Promise((resolve, reject) => {
      this.queue.push({ payload, resolve, reject });
      this.dispatch();
    });
  }

  dispatch() {
    if (this.isClosing || this.queue.length === 0) {
      return;
    }

    const available = this.workers.find((slot) => !slot.busy);
    if (!available) {
      return;
    }

    const task = this.queue.shift();
    available.busy = true;
    available.currentTask = task;
    available.worker.postMessage(task.payload);
  }

  async close() {
    this.isClosing = true;

    while (this.queue.length > 0) {
      const task = this.queue.shift();
      task.reject(new Error('Worker pool closed before completing queued task'));
    }

    await Promise.all(this.workers.map((slot) => slot.worker.terminate()));
  }
}

module.exports = WorkerPool;

