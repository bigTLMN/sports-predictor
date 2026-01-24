export default function Footer() {
  return (
    <footer className="mt-12 py-8 border-t border-slate-200 bg-white">
      <div className="max-w-3xl mx-auto px-4 text-center">
        <h3 className="text-sm font-black text-slate-800 tracking-tight mb-2">
          EDGE ANALYTICS
        </h3>
        <p className="text-[10px] text-slate-400 leading-relaxed max-w-md mx-auto mb-4">
          Data provided for informational purposes only. We do not guarantee the accuracy of predictions. 
          Please bet responsibly. If you or someone you know has a gambling problem, seek help.
        </p>
        <div className="text-[10px] font-bold text-slate-300">
          © {new Date().getFullYear()} AI Sports Prediction Project. Built with Next.js & Python.
        </div>
      </div>
    </footer>
  );
}